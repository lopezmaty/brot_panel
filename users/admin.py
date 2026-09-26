from django.contrib import admin
from . import models

# Register your models here.

@admin.register(models.Perfil)
class PerfilAdmin(admin.ModelAdmin):
    fields = ['usuario', 'nombre', 'rol']
    list_display = ['usuario', 'nombre', 'rol']
