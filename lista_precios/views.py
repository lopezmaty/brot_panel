from django.shortcuts import render
from rest_framework import viewsets
from . import serializers, models

# Create your views here.

class TipoClienteViewset(viewsets.ModelViewSet):
    queryset = models.TipoCliente.objects.all()
    serializer_class = serializers.TipoClienteSerializer

class VariedadViewset(viewsets.ModelViewSet):
    queryset = models.Variedad.objects.all()
    serializer_class = serializers.VariedadSerializer

class TamañoViewset(viewsets.ModelViewSet):
    queryset = models.Tamaño.objects.all()
    serializer_class = serializers.TamañoSerializer

class FamiliaViewset(viewsets.ModelViewSet):
    queryset = models.Familia.objects.all()
    serializer_class = serializers.FamiliaSerializer

class ProductoViewset(viewsets.ModelViewSet):
    queryset = models.Producto.objects.all()
    serializer_class = serializers.ProductoSerializer

class ListaPreciosViewset(viewsets.ModelViewSet):
    queryset = models.ListaPrecios.objects.all()
    serializer_class = serializers.ListaPrecioSerializer

class PreciosViewset(viewsets.ModelViewSet):
    queryset = models.Precio.objects.all()
    serializer_class = serializers.PrecioSerializer