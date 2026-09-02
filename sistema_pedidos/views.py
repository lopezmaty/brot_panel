from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from . import models, serializers
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
        from django.core.mail import send_mail
        pedido = self.get_object()
        estado_anterior = pedido.estado

        response = super().update(request, *args, **kwargs)

        pedido.refresh_from_db()
        estado_nuevo = pedido.estado

        if estado_anterior != estado_nuevo and pedido.cliente.mail:
            mensajes = {
                'en_proceso': (
                    f'Hola {pedido.cliente.nombre},\n\n'
                    f'Tu pedido #{pedido.id:04d} ha sido confirmado y está siendo preparado.\n\n'
                    f'Recordá no tener saldos vencidos para poder proceder con la entrega del mismo. '
                    f'Si no es el caso, por favor contactate con administración al WhatsApp: '
                    f'+54 9 3513 24-3882\n\n'
                    f'Gracias,\nBrot Panes'
                ),
                'completado': (
                    f'Hola {pedido.cliente.nombre},\n\n'
                    f'Tu pedido #{pedido.id:04d} está listo.\n\n'
                    f'Recordá no tener saldos vencidos para poder proceder con la entrega del mismo. '
                    f'Si no es el caso, por favor contactate con administración al WhatsApp: '
                    f'+54 9 3513 24-3882\n\n'
                    f'Gracias,\nBrot Panes'
                ),
                'cancelado': (
                    f'Hola {pedido.cliente.nombre},\n\n'
                    f'Tu pedido #{pedido.id:04d} fue cancelado.\n\n'
                    f'Para más información contactate con administración al WhatsApp: '
                    f'+54 9 3513 24-3882\n\n'
                    f'Gracias,\nBrot Panes'
                ),
            }
            asuntos = {
                'en_proceso': f'Pedido #{pedido.id:04d} confirmado — Brot Panes',
                'completado': f'Pedido #{pedido.id:04d} listo — Brot Panes',
                'cancelado': f'Pedido #{pedido.id:04d} cancelado — Brot Panes',
            }
            mensaje = mensajes.get(estado_nuevo)
            asunto = asuntos.get(estado_nuevo)
            if mensaje:
                send_mail(
                    subject=asunto,
                    message=mensaje,
                    from_email=None,
                    recipient_list=[pedido.cliente.mail],
                    fail_silently=True,
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
    from .xubio import obtener_token, XUBIO_BASE
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

        response = requests.get(
            f'{XUBIO_BASE}/comprobanteVentaBean',
            params={
                'fechaDesde': fecha_desde.strftime('%Y-%m-%d'),
                'fechaHasta': fecha_hasta.strftime('%Y-%m-%d'),
            },
            headers=headers,
        )

        comprobantes = response.json()
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
@permission_classes([IsAuthenticated])
def debug_punto_venta(request):
    from .xubio import obtener_punto_venta
    status_code, texto = obtener_punto_venta(214112)
    return Response({'status': status_code, 'body': texto})