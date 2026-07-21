from rest_framework import serializers
from . import models
from lista_precios.serializers import TipoClienteSerializer, ProductoSerializer
import secrets

class ClienteSerializer(serializers.ModelSerializer):
    tipo_cliente_detalle = TipoClienteSerializer(source='tipo_cliente', read_only=True)
    tipo_cliente = serializers.PrimaryKeyRelatedField(queryset=models.TipoCliente.objects.all())

    class Meta:
        model = models.Cliente
        fields = ['id', 'nombre', 'razon_social','cuit', 'nombre_comercio', 'direccion', 'ciudad', 'provincia', 'telefono', 'mail', 'condicion_iva', 'tipo_cliente', 'tipo_cliente_detalle','activo', 'posee_deuda']

    def create(self, validated_data):
        validated_data['token'] = secrets.token_urlsafe(10)
        return super().create(validated_data)

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

