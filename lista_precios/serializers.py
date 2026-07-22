from rest_framework import serializers
from . import models

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
        
        class Meta:
            model = models.Producto
            fields = ['id', 'nombre', 'variedad', 'variedad_detalle', 'tamaño', 'tamaño_detalle', 'tipo_medida', 'medida_1', 'medida_2', 'medida_3', 'familia', 'familia_detalle', 'unidades_paquete', 'activo']

class ListaPrecioSerializer(serializers.ModelSerializer):
    tipo_cliente = TipoClienteSerializer(read_only=True)

    class Meta:
        model = models.ListaPrecios
        fields = ['id', 'nombre', 'tipo_cliente', 'fecha']

class PrecioSerializer(serializers.ModelSerializer):
    lista_precio = ListaPrecioSerializer(read_only=True)
    producto = ProductoSerializer(read_only=True)

    class Meta:
        model = models.Precio
        fields = ['id', 'lista_precio', 'producto', 'precio']



