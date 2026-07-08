from django.contrib import admin
from . import models

# Register your models here.

@admin.register(models.Cliente)
class ClienteAdmin(admin.ModelAdmin):
    fields = ['nombre', 'razon_social','cuit', 'nombre_comercio', 'direccion', 'ciudad', 'provincia', 'telefono', 'mail', 'condicion_iva', 'tipo_cliente', 'activo']
    search_fields = ['tipo_cliente', 'activo']

@admin.register(models.Pedido)
class PedidoAdmin(admin.ModelAdmin):
    fields = ['cliente', 'estado', 'metodo_entrega']
    search_fields = ['estado', 'metodo_entrega']

@admin.register(models.ItemPedido)
class ItemPedidoAdmin(admin.ModelAdmin):
        fields = ['producto', 'cantidad', 'precio', 'pedido']

