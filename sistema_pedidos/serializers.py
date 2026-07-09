from rest_framework import serializers
from . import models
from lista_precios.serializers import TipoClienteSerializer, ProductoSerializer

class ClienteSerializer(serializers.ModelSerializer):
    tipo_cliente = TipoClienteSerializer(read_only=True)

    class Meta:
        model = models.Cliente
        fields = ['id', 'nombre', 'razon_social','cuit', 'nombre_comercio', 'direccion', 'ciudad', 'provincia', 'telefono', 'mail', 'condicion_iva', 'tipo_cliente', 'activo']

class PedidoSerializer(serializers.ModelSerializer):
    cliente = ClienteSerializer(read_only=True)

    class Meta:
        model = models.Pedido
        fields = ['id', 'cliente', 'estado', 'metodo_entrega']

class ItemPedidoSerializer(serializers.ModelSerializer):
    producto = ProductoSerializer(read_only=True)
    pedido = PedidoSerializer(read_only=True)
    class Meta:
        model = models.ItemPedido
        fields = ['id', 'producto', 'cantidad', 'precio', 'pedido']

