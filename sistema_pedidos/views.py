from django.shortcuts import render
from rest_framework import viewsets
from . import serializers, models
from users.permissions import EsAdmin, EsColab, EsLector
from rest_framework.permissions import IsAuthenticated


# Create your views here.

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

class ItemPedidoViewset(viewsets.ModelViewSet):
    queryset = models.ItemPedido.objects.all()
    serializer_class = serializers.ItemPedidoSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [(EsAdmin | EsColab)()]