from django.urls import path
from . import views
from . import views_rectificaciones as vr

urlpatterns = [
    path('rectificaciones/', vr.rectificaciones, name='ch_rectificaciones'),
    path('rectificaciones/datos-dia/', vr.datos_dia, name='ch_rectificacion_datos_dia'),
    path('rectificaciones/<int:rect_id>/', vr.rectificacion_detalle, name='ch_rectificacion_detalle'),
    path('rectificaciones/<int:rect_id>/pdf/', vr.rectificacion_pdf, name='ch_rectificacion_pdf'),
    path('rectificaciones/<int:rect_id>/foto/', vr.rectificacion_foto, name='ch_rectificacion_foto'),
    path('rectificaciones/<int:rect_id>/resolver/', vr.rectificacion_resolver, name='ch_rectificacion_resolver'),
    path('rectificaciones/<int:rect_id>/anular/', vr.rectificacion_anular, name='ch_rectificacion_anular'),
    path('reporte-mensual/', vr.reporte_mensual, name='ch_reporte_mensual'),
    path('config/', vr.config, name='ch_config'),

    path('empleados/', views.ch_empleados, name='ch_empleados'),
    path('legajos/', views.ch_legajos, name='ch_legajos'),
    path('empleados/update/', views.ch_empleados_update, name='ch_empleados_update'),
    path('empleados/crear/', views.ch_empleado_crear, name='ch_empleado_crear'),
    path('meses/', views.ch_meses, name='ch_meses'),
    path('importar/', views.ch_importar, name='ch_importar'),
    path('preview-empleados/', views.ch_preview_empleados, name='ch_preview_empleados'),
    path('detalle/', views.ch_detalle, name='ch_detalle'),
    path('resumen/', views.ch_resumen, name='ch_resumen'),
    path('cerrar-mes/', views.ch_cerrar_mes, name='ch_cerrar_mes'),
    path('abrir-mes/', views.ch_abrir_mes, name='ch_abrir_mes'),
    path('limpiar-mes/', views.ch_limpiar_mes, name='ch_limpiar_mes'),
    path('evolucion/', views.ch_evolucion, name='ch_evolucion'),
    path('liquidar/', views.ch_liquidar, name='ch_liquidar'),
    path('liquidacion/<int:liq_id>/eliminar/', views.ch_eliminar_liquidacion, name='ch_eliminar_liquidacion'),
    path('ajuste/', views.ch_guardar_ajuste, name='ch_guardar_ajuste'),
    path('data-summary/', views.ch_data_summary, name='ch_data_summary'),
    path('marcar-error-manual/', views.ch_marcar_error_manual, name='ch_marcar_error_manual'),
    path('desmarcar-error-manual/', views.ch_desmarcar_error_manual, name='ch_desmarcar_error_manual'),
]