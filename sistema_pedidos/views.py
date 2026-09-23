from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from . import models, serializers
from django.templatetags.static import static
from lista_precios.services import aplicar_actualizaciones_pendientes
from django.utils import timezone
from users.permissions import EsAdmin, EsColab
from .xubio import obtener_token, XUBIO_BASE
import requests


class ClienteViewSet(viewsets.ModelViewSet):
    queryset = models.Cliente.objects.all()
    serializer_class = serializers.ClienteSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [(EsAdmin | EsColab)()]


class PedidoViewset(viewsets.ModelViewSet):
    queryset = models.Pedido.objects.all()
    serializer_class = serializers.PedidoSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [(EsAdmin | EsColab)()]

    def update(self, request, *args, **kwargs):
        from users.utils import enviar_email_resend
        pedido = self.get_object()
        estado_anterior = pedido.estado

        response = super().update(request, *args, **kwargs)

        pedido.refresh_from_db()
        estado_nuevo = pedido.estado

        if estado_anterior != estado_nuevo and pedido.cliente.mail:

            whatsapp = '+54 9 3513 24-3882'
            logo_url = request.build_absolute_uri(static('img/logo.png'))

            def html_pedido(titulo, mensaje_principal, mostrar_deuda=False):
                deuda_html = f"""
                <p style="color: #444; font-size: 15px; line-height: 1.6; margin: 0 0 16px 0;">
                    Recordá no tener saldos vencidos para poder proceder con la entrega.
                    Si tenés algún saldo pendiente, contactate con administración al WhatsApp:
                    <a href="https://wa.me/5493513243882"
                       style="color: #e8521a;">{whatsapp}</a>
                </p>
                """ if mostrar_deuda else ""

                return f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;
                            padding: 32px; background: #ffffff;">
                    <div style="text-align: center; margin-bottom: 32px;">
                        <img src="{logo_url}" alt="Brot Panes" style="height: 32px;">
                    </div>
                    <div style="background: #f9f9f9; border-radius: 8px; padding: 32px;">
                        <h2 style="color: #1a1a1a; font-size: 20px; margin: 0 0 16px 0;">{titulo}</h2>
                        <p style="color: #444; font-size: 15px; line-height: 1.6; margin: 0 0 16px 0;">
                            Hola {pedido.cliente.nombre},
                        </p>
                        <p style="color: #444; font-size: 15px; line-height: 1.6; margin: 0 0 16px 0;">
                            {mensaje_principal}
                        </p>
                        {deuda_html}
                        <p style="color: #444; font-size: 15px; line-height: 1.6; margin: 0;">
                            Gracias por elegirnos.
                        </p>
                    </div>
                    <p style="color: #aaa; font-size: 12px; text-align: center; margin-top: 24px;">
                        Brot Panes · Córdoba, Argentina
                    </p>
                </div>
                """

            configs = {
                'en_proceso': {
                    'asunto': f'Pedido #{pedido.id:04d} confirmado — Brot Panes',
                    'texto': (
                        f'Hola {pedido.cliente.nombre},\n\n'
                        f'Tu pedido #{pedido.id:04d} ha sido confirmado y está siendo preparado.\n\n'
                        f'Recordá no tener saldos vencidos para poder proceder con la entrega. '
                        f'Contactate con administración al WhatsApp: {whatsapp}\n\nGracias,\nBrot Panes'
                    ),
                    'html': html_pedido(
                        f'Pedido #{pedido.id:04d} confirmado',
                        f'Tu pedido <strong>#{pedido.id:04d}</strong> fue confirmado y está siendo preparado.',
                        mostrar_deuda=True,
                    ),
                },
                'completado': {
                    'asunto': f'Pedido #{pedido.id:04d} listo — Brot Panes',
                    'texto': (
                        f'Hola {pedido.cliente.nombre},\n\n'
                        f'Tu pedido #{pedido.id:04d} está listo.\n\n'
                        f'Recordá no tener saldos vencidos para poder proceder con la entrega. '
                        f'Contactate con administración al WhatsApp: {whatsapp}\n\nGracias,\nBrot Panes'
                    ),
                    'html': html_pedido(
                        f'Pedido #{pedido.id:04d} listo',
                        f'Tu pedido <strong>#{pedido.id:04d}</strong> está listo para ser entregado.',
                        mostrar_deuda=True,
                    ),
                },
                'cancelado': {
                    'asunto': f'Pedido #{pedido.id:04d} cancelado — Brot Panes',
                    'texto': (
                        f'Hola {pedido.cliente.nombre},\n\n'
                        f'Tu pedido #{pedido.id:04d} fue cancelado.\n\n'
                        f'Para más información contactate al WhatsApp: {whatsapp}\n\nGracias,\nBrot Panes'
                    ),
                    'html': html_pedido(
                        f'Pedido #{pedido.id:04d} cancelado',
                        f'Tu pedido <strong>#{pedido.id:04d}</strong> fue cancelado. '
                        f'Para más información contactate con administración al WhatsApp: '
                        f'<a href="https://wa.me/5493513243882" style="color: #e8521a;">{whatsapp}</a>',
                        mostrar_deuda=False,
                    ),
                },
            }

            config = configs.get(estado_nuevo)
            if config:
                enviar_email_resend(
                    pedido.cliente.mail,
                    config['asunto'],
                    config['texto'],
                    config['html'],
                )

        return response


class ItemPedidoViewset(viewsets.ModelViewSet):
    queryset = models.ItemPedido.objects.all()
    serializer_class = serializers.ItemPedidoSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [(EsAdmin | EsColab)()]


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def pedidos_nuevos(request):
    ultimo_id = request.GET.get('ultimo_id', 0)
    cantidad = models.Pedido.objects.filter(id__gt=ultimo_id).count()
    return Response({'cantidad': cantidad})


@api_view(['POST'])
@permission_classes([EsAdmin | EsColab])
def facturar_pedidos(request):
    from .xubio import facturar_pedido
    ids = request.data.get('pedido_ids', [])
    if not ids:
        return Response({'error': 'No se enviaron pedidos.'}, status=400)

    resultados = []
    for pedido_id in ids:
        try:
            pedido = models.Pedido.objects.get(id=pedido_id)
            status_code, respuesta = facturar_pedido(pedido)
            resultados.append({
                'pedido_id': pedido_id,
                'ok': status_code in [200, 201],
                'detalle': respuesta,
            })
        except models.Pedido.DoesNotExist:
            resultados.append({'pedido_id': pedido_id, 'ok': False, 'detalle': 'Pedido no encontrado'})
        except Exception as e:
            resultados.append({'pedido_id': pedido_id, 'ok': False, 'detalle': str(e)})

    return Response(resultados)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def buscar_cliente_xubio(request):
    cuit = request.GET.get('cuit', '')
    if not cuit:
        return Response({'error': 'CUIT requerido'}, status=400)

    try:
        token = obtener_token()
        response = requests.get(
            f'{XUBIO_BASE}/clienteBean',
            params={'numeroIdentificacion': cuit},
            headers={
                'Authorization': f'Bearer {token}',
                'Accept': 'application/json',
            }
        )
        data = response.json()
        if not data:
            return Response({'error': 'No se encontró el cliente en Xubio'}, status=404)

        cliente = data[0]
        categoria = cliente.get('categoriaFiscal', {}).get('codigo', '')
        condicion_iva_map = {
            'RI': 'responsable_inscripto',
            'MT': 'monotributista',
            'CF': 'consumidor_final',
        }

        return Response({
            'xubio_cliente_id': cliente.get('cliente_id'),
            'razon_social': cliente.get('razonSocial', ''),
            'direccion': cliente.get('direccion', ''),
            'mail': cliente.get('email', ''),
            'telefono': cliente.get('telefono', ''),
            'condicion_iva': condicion_iva_map.get(categoria, ''),
            'provincia': cliente.get('provincia', {}).get('nombre', ''),
        })

    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([])
@authentication_classes([])
def confirmar_pedido_catalogo(request, token):
    from lista_precios.models import Precio as PrecioModel, Producto as ProductoModel

    cliente = get_object_or_404(models.Cliente, token=token, activo=True)

    items = request.data.get('items', [])
    metodo_entrega = request.data.get('metodo_entrega', '')
    observaciones = request.data.get('observaciones', '')

    if not items:
        return Response({'error': 'Sin items'}, status=400)

    if metodo_entrega == 'retiro' and not cliente.permite_retiro:
        return Response({'error': 'Método no habilitado'}, status=400)
    if metodo_entrega == 'entrega_domicilio' and not cliente.permite_domicilio:
        return Response({'error': 'Método no habilitado'}, status=400)

    pedido = models.Pedido.objects.create(
        cliente=cliente,
        metodo_entrega=metodo_entrega,
        observaciones=observaciones or None,
    )

    lista = cliente.lista_precios
    if lista:
        aplicar_actualizaciones_pendientes(lista)
    for item in items:
        producto = get_object_or_404(ProductoModel, id=item['producto_id'], activo=True)
        try:
            precio_obj = PrecioModel.objects.get(lista_precio=lista, producto=producto)
            precio = precio_obj.precio
        except PrecioModel.DoesNotExist:
            precio = 0

        models.ItemPedido.objects.create(
            pedido=pedido,
            producto=producto,
            cantidad=item['cantidad'],
            precio=precio,
        )

    return Response({'pedido_id': pedido.id}, status=201)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ventas_xubio_15dias(request):
    from .xubio import obtener_token, XUBIO_BASE, _paginar_comprobantes
    from datetime import date, timedelta
    from concurrent.futures import ThreadPoolExecutor, as_completed

    fecha_hasta = date.today()
    fecha_desde = fecha_hasta - timedelta(days=15)

    try:
        token = obtener_token()
        headers = {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/json',
        }

        comprobantes = _paginar_comprobantes(
            f'{XUBIO_BASE}/comprobanteVentaBean',
            fecha_desde.strftime('%Y-%m-%d'),
            fecha_hasta.strftime('%Y-%m-%d'),
            headers,
        )

        ventas = {}

        def traer_detalle(transaccion_id):
            try:
                r = requests.get(
                    f'{XUBIO_BASE}/comprobanteVentaBean/{transaccion_id}',
                    headers=headers,
                    timeout=10,
                )
                if r.status_code == 200:
                    return r.json().get('transaccionProductoItems', [])
            except Exception:
                pass
            return []

        ids = [c.get('transaccionid') for c in comprobantes if c.get('transaccionid')]

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(traer_detalle, tid): tid for tid in ids}
            for future in as_completed(futures):
                items = future.result()
                for item in items:
                    producto = item.get('producto', {})
                    producto_id = producto.get('id') or producto.get('ID')
                    cantidad = item.get('cantidad', 0)
                    if producto_id and cantidad:
                        ventas[producto_id] = ventas.get(producto_id, 0) + cantidad

        return Response({
            'ventas': ventas,
            'fecha_desde': fecha_desde.strftime('%d/%m/%Y'),
            'fecha_hasta': fecha_hasta.strftime('%d/%m/%Y'),
        })

    except Exception as e:
        print(f"Xubio ventas error: {str(e)}")
        return Response({'error': str(e)}, status=500)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def stock_productos(request):
    if request.method == 'GET':
        stocks = models.StockProducto.objects.all()
        data = {s.xubio_producto_id: s.stock_actual for s in stocks}
        return Response(data)

    if request.method == 'POST':
        items = request.data.get('items', [])
        for item in items:
            models.StockProducto.objects.update_or_create(
                xubio_producto_id=item['xubio_producto_id'],
                defaults={
                    'nombre': item['nombre'],
                    'stock_actual': item['stock_actual'],
                }
            )
        return Response({'ok': True})


@api_view(['GET'])
@permission_classes([])
@authentication_classes([])
def comunicaciones_pendientes_catalogo(request, token):
    """Comunicaciones sin leer de este cliente (avisos de lista de precios y
    comunicaciones generales). Esto alimenta el popup del catálogo."""
    from lista_precios.models import ActualizacionPrecios

    cliente = get_object_or_404(models.Cliente, token=token, activo=True)

    pendientes = models.ComunicacionDestinatario.objects.filter(
        cliente=cliente, leida_en__isnull=True
    ).select_related('comunicacion', 'comunicacion__actualizacion').order_by('comunicacion__creada')

    data = []
    for destinatario in pendientes:
        comunicacion = destinatario.comunicacion
        vigente_desde = None
        if comunicacion.actualizacion:
            vigente_desde = timezone.localtime(comunicacion.actualizacion.vigente_desde).strftime('%d/%m/%Y')
        data.append({
            'id': comunicacion.id,
            'titulo': comunicacion.titulo,
            'mensaje': comunicacion.mensaje,
            'origen': comunicacion.origen,
            'vigente_desde': vigente_desde,
        })

    return Response({'comunicaciones': data})


@api_view(['POST'])
@permission_classes([])
@authentication_classes([])
def confirmar_lectura_comunicacion(request, token, comunicacion_id):
    """El cliente confirma que leyó una comunicación (botón del popup)."""
    cliente = get_object_or_404(models.Cliente, token=token, activo=True)
    destinatario = get_object_or_404(
        models.ComunicacionDestinatario,
        comunicacion_id=comunicacion_id, cliente=cliente, leida_en__isnull=True,
    )
    destinatario.leida_en = timezone.now()
    destinatario.save(update_fields=['leida_en'])
    return Response({'ok': True})


def _html_comunicacion_manual(titulo, mensaje, logo_url):
    """Mismo estilo Brot Panes que los otros mails del sistema, para una
    comunicación general (no ligada a una lista de precios)."""
    mensaje_html = mensaje.replace('\n', '<br>')
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;
                padding: 32px; background: #ffffff;">
        <div style="text-align: center; margin-bottom: 32px;">
            <img src="{logo_url}" alt="Brot Panes" style="height: 32px;">
        </div>
        <div style="background: #f9f9f9; border-radius: 8px; padding: 32px;">
            <h2 style="color: #1a1a1a; font-size: 20px; margin: 0 0 16px 0;">{titulo}</h2>
            <p style="color: #444; font-size: 15px; line-height: 1.6; margin: 0;">
                {mensaje_html}
            </p>
        </div>
        <p style="color: #aaa; font-size: 12px; text-align: center; margin-top: 24px;">
            Brot Panes · Córdoba, Argentina
        </p>
    </div>
    """


@api_view(['GET'])
@permission_classes([EsAdmin])
def comunicaciones_opciones(request):
    """Datos para armar el modal de "Nueva comunicación": listas de precios,
    tipos de cliente, y cada cliente activo con su lista/tipo (para el
    contador de destinatarios en vivo) y si tiene mail cargado."""
    from lista_precios.models import ListaPrecios, TipoCliente

    clientes = models.Cliente.objects.filter(activo=True).order_by('nombre_comercio', 'nombre')

    return Response({
        'listas': [{'id': l.id, 'nombre': l.nombre} for l in ListaPrecios.objects.order_by('nombre')],
        'tipos': [{'id': t.id, 'nombre': t.nombre} for t in TipoCliente.objects.order_by('nombre')],
        'clientes': [
            {
                'id': c.id,
                'nombre': c.nombre_comercio or c.razon_social or c.nombre,
                'lista_id': c.lista_precios_id,
                'tipo_id': c.tipo_cliente_id,
                'tiene_mail': bool(c.mail),
            }
            for c in clientes
        ],
    })


def _ids(valor):
    try:
        return [int(x) for x in (valor or [])]
    except (TypeError, ValueError):
        return []


@api_view(['POST'])
@permission_classes([EsAdmin])
def comunicaciones_enviar(request):
    """Crea una Comunicacion general (origen='manual') y la manda por popup +
    mail a los destinatarios elegidos. Los criterios se combinan (unión):
    "todos" ignora el resto; si no, cliente puntual + lista + tipo se suman."""
    from users.utils import enviar_email_resend
    from django.db.models import Q

    titulo = (request.data.get('titulo') or '').strip()
    mensaje = (request.data.get('mensaje') or '').strip()
    if not titulo or not mensaje:
        return Response({'error': 'Completá el título y el mensaje.'}, status=400)
    if len(titulo) > 120:
        return Response({'error': 'El título es demasiado largo (máximo 120 caracteres).'}, status=400)

    todos = bool(request.data.get('todos'))
    lista_ids = _ids(request.data.get('listas'))
    tipo_ids = _ids(request.data.get('tipos'))
    cliente_ids = _ids(request.data.get('clientes'))

    clientes_qs = models.Cliente.objects.filter(activo=True)
    if not todos:
        filtro = Q()
        hay_criterio = False
        if cliente_ids:
            filtro |= Q(id__in=cliente_ids)
            hay_criterio = True
        if lista_ids:
            filtro |= Q(lista_precios_id__in=lista_ids)
            hay_criterio = True
        if tipo_ids:
            filtro |= Q(tipo_cliente_id__in=tipo_ids)
            hay_criterio = True
        if not hay_criterio:
            return Response({'error': 'Elegí al menos un destinatario.'}, status=400)
        clientes_qs = clientes_qs.filter(filtro)

    if not clientes_qs.exists():
        return Response({'error': 'No hay clientes activos que coincidan con lo elegido.'}, status=400)

    comunicacion = models.Comunicacion.objects.create(
        titulo=titulo, mensaje=mensaje, origen='manual', creada_por=request.user,
    )
    logo_url = request.build_absolute_uri(static('img/logo.png'))
    html = _html_comunicacion_manual(titulo, mensaje, logo_url)

    for cliente in clientes_qs.distinct():
        destinatario = models.ComunicacionDestinatario.objects.create(
            comunicacion=comunicacion, cliente=cliente,
        )
        if cliente.mail:
            try:
                enviar_email_resend(cliente.mail, f'{titulo} — Brot Panes', mensaje, html)
                destinatario.mail_enviado = True
                destinatario.save(update_fields=['mail_enviado'])
            except Exception:
                pass  # el aviso ya quedó visible en el catálogo aunque el mail falle

    return Response({
        'comunicacion_id': comunicacion.id,
        'destinatarios': clientes_qs.distinct().count(),
    }, status=201)