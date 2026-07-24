from django.shortcuts import render
from rest_framework import viewsets
from . import serializers, models
from users.permissions import EsAdmin, EsColab, EsLector
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

# Create your views here.

class TipoClienteViewset(viewsets.ModelViewSet):
    queryset = models.TipoCliente.objects.all()
    serializer_class = serializers.TipoClienteSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [EsAdmin()]

class VariedadViewset(viewsets.ModelViewSet):
    queryset = models.Variedad.objects.all()
    serializer_class = serializers.VariedadSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [EsAdmin()]    

class TamañoViewset(viewsets.ModelViewSet):
    queryset = models.Tamaño.objects.all()
    serializer_class = serializers.TamañoSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [EsAdmin()]

class FamiliaViewset(viewsets.ModelViewSet):
    queryset = models.Familia.objects.all()
    serializer_class = serializers.FamiliaSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [EsAdmin()]

class ProductoViewset(viewsets.ModelViewSet):
    queryset = models.Producto.objects.all()
    serializer_class = serializers.ProductoSerializer

    def get_permissions(self):
            if self.action in ['list', 'retrieve']:
                return [IsAuthenticated()]
            return [(EsAdmin | EsColab)()]
    
class ListaPreciosViewset(viewsets.ModelViewSet):
    queryset = models.ListaPrecios.objects.all()
    serializer_class = serializers.ListaPrecioSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [EsAdmin()]

class PreciosViewset(viewsets.ModelViewSet):
    queryset = models.Precio.objects.all()
    serializer_class = serializers.PrecioSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [EsAdmin()]

@api_view(['POST'])
@permission_classes([EsAdmin])
def guardar_lista_completa(request):
    nombre = request.data.get('nombre')
    fecha = request.data.get('fecha')
    lista_id = request.data.get('lista_id')
    precios = request.data.get('precios')
    tipo_cliente = request.data.get('tipo_cliente')

    if lista_id:
        lista = models.ListaPrecios.objects.get(pk=lista_id)
        lista.nombre = nombre
        lista.fecha = fecha
        lista.tipo_cliente_id = tipo_cliente
        lista.save()
    else:
        lista = models.ListaPrecios.objects.create(nombre=nombre, fecha=fecha, tipo_cliente=tipo_cliente)

    for item in precios:
        producto_id = item.get('producto')
        precio_valor = item.get('precio')
        models.Precio.objects.update_or_create(
            lista_precio=lista,
            producto_id=producto_id,
            defaults={'precio': precio_valor}
        )

    return Response({'id': lista.id}, status=201)