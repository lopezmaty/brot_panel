from django.shortcuts import render
from rest_framework import viewsets
from . import serializers, models
from users.permissions import EsAdmin, EsColab, EsLector
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.contrib.auth.decorators import login_required
from sistema_pedidos import xubio
from . import models

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

class HistorialPrecioViewset(viewsets.ReadOnlyModelViewSet):
    queryset = models.HistorialPrecio.objects.all().select_related('producto', 'lista_precio')
    serializer_class = serializers.HistorialPrecioSerializer

    def get_permissions(self):
        return [IsAuthenticated()]


@api_view(['POST'])
@permission_classes([EsAdmin])
def guardar_lista_completa(request):
    fecha = request.data.get('fecha')
    lista_id = request.data.get('lista_id')
    nombre = request.data.get('nombre')
    xubio_lista_precio_id = request.data.get('xubio_lista_precio_id')

    if lista_id:
        lista = models.ListaPrecios.objects.get(pk=lista_id)
        lista.nombre = nombre
        lista.fecha = fecha
        lista.xubio_lista_precio_id = xubio_lista_precio_id or None
        lista.save()
    else:
        lista = models.ListaPrecios.objects.create(
            nombre=nombre,
            fecha=fecha,
            xubio_lista_precio_id=xubio_lista_precio_id or None,
        )

    return Response({'id': lista.id}, status=201)


@api_view(['POST'])
@permission_classes([EsAdmin])
def importar_precios_xubio(request, lista_id):
    lista = models.ListaPrecios.objects.get(pk=lista_id)

    if not lista.xubio_lista_precio_id:
        return Response(
            {'error': 'Esta lista no tiene un código de lista de precios de Xubio asignado.'},
            status=400,
        )

    items_xubio = xubio.obtener_precios_lista(lista.xubio_lista_precio_id)

    productos_por_xubio_id = {
        p.xubio_producto_id: p
        for p in models.Producto.objects.exclude(xubio_producto_id__isnull=True)
    }

    precios_actuales = {
        precio.producto_id: precio.precio
        for precio in models.Precio.objects.filter(lista_precio=lista)
    }

    importados = 0
    con_cambio_de_precio = 0
    sin_match = []

    for item in items_xubio:
        producto_xubio = item.get('producto') or {}
        xubio_producto_id = producto_xubio.get('id')
        precio_valor = item.get('precio')

        producto = productos_por_xubio_id.get(xubio_producto_id)
        if producto is None:
            sin_match.append(producto_xubio.get('nombre') or xubio_producto_id)
            continue

        precio_anterior = precios_actuales.get(producto.id)

        if precio_anterior is None or float(precio_anterior) != float(precio_valor):
            models.HistorialPrecio.objects.create(
                lista_precio=lista,
                producto=producto,
                precio=precio_valor,
            )
            con_cambio_de_precio += 1

        models.Precio.objects.update_or_create(
            lista_precio=lista,
            producto=producto,
            defaults={'precio': precio_valor},
        )
        importados += 1

    return Response({
        'importados': importados,
        'con_cambio_de_precio': con_cambio_de_precio,
        'sin_match': sin_match,
    })