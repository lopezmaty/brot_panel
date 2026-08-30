from rest_framework import serializers
from . import models
from lista_precios.serializers import TipoClienteSerializer, ProductoSerializer, ListaPrecioSerializer
import secrets
from .xubio import crear_cliente_en_xubio

class ClienteSerializer(serializers.ModelSerializer):
    tipo_cliente_detalle = TipoClienteSerializer(source='tipo_cliente', read_only=True)
    tipo_cliente = serializers.PrimaryKeyRelatedField(queryset=models.TipoCliente.objects.all())
    lista_precios_detalle = ListaPrecioSerializer(source='lista_precios', read_only=True)
    lista_precios = serializers.PrimaryKeyRelatedField(queryset=models.ListaPrecios.objects.all())

    class Meta:
        model = models.Cliente
        fields = [
            'id', 'nombre', 'razon_social', 'cuit', 'nombre_comercio',
            'direccion', 'ciudad', 'provincia', 'telefono', 'mail',
            'condicion_iva', 'tipo_cliente', 'tipo_cliente_detalle',
            'activo', 'posee_deuda', 'lista_precios', 'lista_precios_detalle',
            'xubio_cliente_id', 'xubio_punto_venta_id', 'xubio_tipo_comprobante', 'dias_cc',
            'permite_retiro', 'permite_domicilio',
        ]

    def create(self, validated_data):
        validated_data['token'] = secrets.token_urlsafe(10)
        cliente = super().create(validated_data)

        try:
            xubio_id = crear_cliente_en_xubio(cliente)
            if xubio_id:
                cliente.xubio_cliente_id = xubio_id
                cliente.save(update_fields=['xubio_cliente_id'])
        except Exception:
            pass

        return cliente


class PedidoSerializer(serializers.ModelSerializer):
    cliente = ClienteSerializer(read_only=True)
    metodo_entrega = serializers.CharField(required=False)

    class Meta:
        model = models.Pedido
        fields = ['id', 'cliente', 'estado', 'metodo_entrega']


class ItemPedidoSerializer(serializers.ModelSerializer):
    producto = ProductoSerializer(read_only=True)
    pedido = PedidoSerializer(read_only=True)

    class Meta:
        model = models.ItemPedido
        fields = ['id', 'producto', 'cantidad', 'precio', 'pedido']