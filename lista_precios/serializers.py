from rest_framework import serializers
from . import models
from sistema_pedidos.models import Cliente

class TipoClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.TipoCliente
        fields = ['id', 'nombre']

class VariedadSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Variedad
        fields = ['id', 'nombre']

class TamañoSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Tamaño
        fields = ['id', 'nombre']

class FamiliaSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Familia
        fields = ['id', 'nombre']

class ProductoSerializer(serializers.ModelSerializer):
    variedad_detalle = VariedadSerializer(source='variedad', read_only=True)
    variedad = serializers.PrimaryKeyRelatedField(queryset=models.Variedad.objects.all())
    tamaño_detalle = TamañoSerializer(source='tamaño', read_only=True)
    tamaño = serializers.PrimaryKeyRelatedField(queryset=models.Tamaño.objects.all())
    familia_detalle = FamiliaSerializer(source='familia', read_only=True)
    familia = serializers.PrimaryKeyRelatedField(queryset=models.Familia.objects.all())
    clientes_exclusivos = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Cliente.objects.all(),
        required=False,
    )

    class Meta:
        model = models.Producto
        fields = [
            'id', 'nombre', 'variedad', 'variedad_detalle', 'tamaño', 'tamaño_detalle',
            'tipo_medida', 'medida_1', 'medida_2', 'medida_3', 'familia', 'familia_detalle',
            'unidades_paquete', 'activo', 'xubio_producto_id', 'clientes_exclusivos',
        ]

    def update(self, instance, validated_data):
        clientes_exclusivos = validated_data.pop('clientes_exclusivos', None)
        instance = super().update(instance, validated_data)
        if clientes_exclusivos is not None:
            instance.clientes_exclusivos.set(clientes_exclusivos)
        return instance

    def create(self, validated_data):
        clientes_exclusivos = validated_data.pop('clientes_exclusivos', None)
        instance = super().create(validated_data)
        if clientes_exclusivos is not None:
            instance.clientes_exclusivos.set(clientes_exclusivos)
        return instance

class ListaPrecioSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ListaPrecios
        fields = ['id', 'nombre', 'fecha', 'xubio_lista_precio_id']

class PrecioSerializer(serializers.ModelSerializer):
    lista_precio = ListaPrecioSerializer(read_only=True)
    producto = ProductoSerializer(read_only=True)

    class Meta:
        model = models.Precio
        fields = ['id', 'lista_precio', 'producto', 'precio']

class HistorialPrecioSerializer(serializers.ModelSerializer):
    producto = ProductoSerializer(read_only=True)
    lista_precio = ListaPrecioSerializer(read_only=True)

    class Meta:
        model = models.HistorialPrecio
        fields = ['id', 'lista_precio', 'producto', 'precio', 'fecha']