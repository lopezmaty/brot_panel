from datetime import datetime, time
from decimal import Decimal, InvalidOperation

import requests
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets
from . import serializers, models
from users.permissions import EsAdmin, EsColab, EsLector
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from sistema_pedidos import xubio

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
    """Trae los precios de Xubio y los deja PROGRAMADOS para una fecha futura.
    No modifica Precio: eso ocurre cuando llega la vigencia."""
    lista = get_object_or_404(models.ListaPrecios, pk=lista_id)

    if not lista.xubio_lista_precio_id:
        return Response(
            {'error': 'Esta lista no tiene un código de lista de precios de Xubio asignado.'},
            status=400,
        )

    # 1) Fecha de vigencia: obligatoria y posterior a hoy
    try:
        fecha = datetime.strptime(request.data.get('vigente_desde'), '%Y-%m-%d').date()
    except (TypeError, ValueError):
        return Response({'error': 'Indicá la fecha de vigencia (formato AAAA-MM-DD).'}, status=400)

    if fecha <= timezone.localdate():
        return Response({'error': 'La fecha de vigencia debe ser posterior a hoy.'}, status=400)

    # 00:00 hora de Córdoba (usa TIME_ZONE de settings)
    vigente_desde = timezone.make_aware(datetime.combine(fecha, time.min))

    # 2) Una sola programada por lista
    if models.ActualizacionPrecios.objects.filter(lista_precio=lista, estado='programada').exists():
        return Response(
            {'error': 'Esta lista ya tiene una actualización programada. Cancelala antes de cargar otra.'},
            status=409,
        )

    # 3) Traer de Xubio
    try:
        items_xubio = xubio.obtener_precios_lista(lista.xubio_lista_precio_id)
    except requests.RequestException as e:
        return Response({'error': f'No se pudo consultar Xubio: {e}'}, status=502)

    productos_por_xubio_id = {
        p.xubio_producto_id: p
        for p in models.Producto.objects.exclude(xubio_producto_id__isnull=True)
    }
    precios_actuales = {
        p.producto_id: p.precio
        for p in models.Precio.objects.filter(lista_precio=lista)
    }

    # 4) Quedarse solo con lo que cambió o es nuevo
    cambios = []
    sin_match = []

    for item in items_xubio:
        producto_xubio = item.get('producto') or {}
        xubio_producto_id = producto_xubio.get('id')

        producto = productos_por_xubio_id.get(xubio_producto_id)
        if producto is None:
            sin_match.append(producto_xubio.get('nombre') or xubio_producto_id)
            continue

        try:
            precio_nuevo = Decimal(str(item.get('precio'))).quantize(Decimal('0.01'))
        except InvalidOperation:
            continue

        precio_anterior = precios_actuales.get(producto.id)
        if precio_anterior is not None and precio_anterior == precio_nuevo:
            continue

        cambios.append((producto, precio_anterior, precio_nuevo))

    if not cambios:
        return Response(
            {'error': 'Los precios de Xubio son iguales a los vigentes. No hay nada para programar.',
             'sin_match': sin_match},
            status=400,
        )

    # 5) Guardar todo junto o nada
    with transaction.atomic():
        actualizacion = models.ActualizacionPrecios.objects.create(
            lista_precio=lista,
            vigente_desde=vigente_desde,
            creada_por=request.user,
        )
        models.ItemActualizacionPrecios.objects.bulk_create([
            models.ItemActualizacionPrecios(
                actualizacion=actualizacion,
                producto=producto,
                precio_anterior=anterior,
                precio_nuevo=nuevo,
            )
            for producto, anterior, nuevo in cambios
        ])

    return Response({
        'actualizacion_id': actualizacion.id,
        'vigente_desde': vigente_desde.isoformat(),
        'cantidad_cambios': len(cambios),
        'sin_match': sin_match,
        'cambios': [
            {'producto': str(p), 'anterior': a, 'nuevo': n}
            for p, a, n in cambios
        ],
    }, status=201)


@api_view(['POST'])
@permission_classes([EsAdmin])
def cancelar_actualizacion(request, actualizacion_id):
    actualizacion = get_object_or_404(
        models.ActualizacionPrecios, pk=actualizacion_id, estado='programada'
    )
    actualizacion.estado = 'cancelada'
    actualizacion.save(update_fields=['estado'])
    return Response({'ok': True})