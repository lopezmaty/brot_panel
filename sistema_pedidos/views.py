from django.shortcuts import render
from rest_framework import viewsets
from . import serializers, models
from users.permissions import EsAdmin, EsColab, EsLector
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.core.mail import send_mail


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