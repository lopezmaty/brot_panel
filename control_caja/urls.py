from django.urls import path
from . import views

urlpatterns = [
    path('', views.control_caja_view, name='control_caja'),
    path('api/movimientos/', views.api_movimientos, name='api_movimientos'),
    path('api/movimientos/<int:pk>/', views.api_movimiento_detalle, name='api_movimiento_detalle'),
    path('api/saldo-inicial/', views.api_saldo_inicial, name='api_saldo_inicial'),
    path('api/cierre-diario/', views.api_cierre_diario, name='api_cierre_diario'),
    path('api/cierre-diario/<int:pk>/', views.api_cierre_diario_detalle, name='api_cierre_diario_detalle'),
    path('api/conciliacion/importar/', views.api_conciliacion_importar, name='api_conciliacion_importar'),
    path('api/conciliacion/', views.api_conciliacion_listar, name='api_conciliacion_listar'),
    path('api/resumen-mensual/', views.api_resumen_mensual, name='api_resumen_mensual'),
]