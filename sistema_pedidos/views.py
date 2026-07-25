from django.shortcuts import render
from rest_framework import viewsets
from . import serializers, models
from users.permissions import EsAdmin, EsColab, EsLector
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response


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