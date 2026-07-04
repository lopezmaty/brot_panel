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
        variedad = VariedadSerializer(read_only=True)
        tamaño = TamañoSerializer(read_only=True)
        familia = FamiliaSerializer(read_only=True)
        
        class Meta:
            model = models.Producto
            fields = ['id', 'nombre', 'variedad', 'tamaño', 'tipo_medida', 'medida_1', 'medida_2', 'medida_3', 'familia', 'unidades_paquete', 'activo']

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



