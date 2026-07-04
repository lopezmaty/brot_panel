from django.contrib import admin
from . import models

# Register your models here.

@admin.register(models.Producto)
class AdminProducto(admin.ModelAdmin):
    fields = ['nombre', 'variedad', 'tamaño', 'tipo_medida', 'medida_1', 'medida_2', 'medida_3', 'familia', 'unidades_paquete', 'activo']
    search_fields = ['variedad', 'familia']

@admin.register(models.Precio)
class AdminPrecio(admin.ModelAdmin):
    fields = ['lista_precio', 'producto', 'precio']
    search_fields = ['lista_precio', 'producto']

@admin.register(models.TipoCliente)
class AdminTipoCliente(admin.ModelAdmin):
    fields = ['nombre']

@admin.register(models.ListaPrecios)
class AdminListaPrecios(admin.ModelAdmin):
    fields = ['nombre', 'tipo_cliente', 'fecha']
    search_fields = ['tipo_cliente']

@admin.register(models.Variedad)
class AdminVariedad(admin.ModelAdmin):
    fields = ['nombre']

@admin.register(models.Tamaño)
class AdminTamaño(admin.ModelAdmin):
    fields = ['nombre']

@admin.register(models.Familia)
class AdminFamilia(admin.ModelAdmin):
    fields = ['nombre']