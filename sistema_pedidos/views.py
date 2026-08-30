from django.shortcuts import render
from rest_framework import viewsets
from . import serializers, models
from users.permissions import EsAdmin, EsColab, EsLector
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.core.mail import send_mail
from .xubio import obtener_token, XUBIO_BASE
import requests
from lista_precios.models import Precio as PrecioModel



# Create your views here.

class ClienteViewSet(viewsets.ModelViewSet):
    queryset = models.Cliente.objects.all().order_by("razon_social")
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


@api_view(['POST'])
@permission_classes([EsAdmin])
def aplicar_lista_a_todos(request):
    lista_id = request.data.get('lista_id')
    lista_precios = models.ListaPrecios.objects.get(pk=lista_id)
    categoria = lista_precios.tipo_cliente
    clientes_a_actualizar = models.Cliente.objects.filter(lista_precios__tipo_cliente=categoria).update(lista_precios=lista_precios)

    return Response({'clientes_a_actualizar': clientes_a_actualizar}, status=200)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def pedidos_nuevos(request):
    ultimo_id = request.GET.get('ultimo_id', 0)
    cantidad = models.Pedido.objects.filter(id__gt=ultimo_id).count()
    return Response({'cantidad': cantidad})

from .xubio import facturar_pedido

@api_view(['POST'])
@permission_classes([EsAdmin | EsColab])
def facturar_pedidos(request):
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
def confirmar_pedido_catalogo(request, token):
    cliente = get_object_or_404(Cliente, token=token, activo=True)

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
        producto = get_object_or_404(models.Producto, id=item['producto_id'], activo=True)
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