from django.contrib import admin

from .models import AvisoEnviado, Ausencia, DocumentacionEmpleado, DocumentoPersonal, Empleado, Novedad


@admin.register(Empleado)
class EmpleadoAdmin(admin.ModelAdmin):
    list_display = ("nombre_completo", "dni", "puesto", "fecha_ingreso", "estado")
    list_filter = ("estado", "puesto")
    search_fields = ("nombre", "apellido", "dni")


@admin.register(DocumentacionEmpleado)
class DocumentacionEmpleadoAdmin(admin.ModelAdmin):
    list_display = ("empleado", "tipo", "fecha_vencimiento", "estado_vencimiento")
    list_filter = ("tipo",)
    search_fields = ("empleado__nombre", "empleado__apellido")


@admin.register(DocumentoPersonal)
class DocumentoPersonalAdmin(admin.ModelAdmin):
    list_display = ("empleado", "tipo", "fecha", "estado")
    list_filter = ("tipo", "estado")
    search_fields = ("empleado__nombre", "empleado__apellido")


@admin.register(Ausencia)
class AusenciaAdmin(admin.ModelAdmin):
    list_display = ("empleado", "tipo", "fecha_desde", "fecha_hasta", "justificada")
    list_filter = ("tipo", "justificada")


@admin.register(Novedad)
class NovedadAdmin(admin.ModelAdmin):
    list_display = ("fecha", "empleado", "tipo")
    list_filter = ("tipo",)


@admin.register(AvisoEnviado)
class AvisoEnviadoAdmin(admin.ModelAdmin):
    list_display = ("tipo", "referencia_id", "fecha_aviso", "enviado_en")
    list_filter = ("tipo",)