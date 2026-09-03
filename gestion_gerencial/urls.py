from django.urls import path
from . import views

urlpatterns = [
    path('importar-compras-xubio/', views.importar_compras_xubio, name='importar_compras_xubio_mapa'),
    path('importar-ventas-xubio/', views.importar_ventas_xubio, name='importar_ventas_xubio_mapa'),
    path('compras/', views.listar_compras_mes, name='listar_compras_mes'),
    path('asignar-rubro-compra/', views.asignar_rubro_compra, name='asignar_rubro_compra'),
    path('datos-mes/', views.obtener_datos_mes, name='obtener_datos_mes'),
    path('guardar-datos-mes/', views.guardar_datos_mes, name='guardar_datos_mes'),
    path('ventas-detalle/', views.ventas_detalle_mes, name='ventas_detalle_mes'),
    path('dashboard-mes/', views.dashboard_mes, name='dashboard_mes_mapa'),
    path('historico/', views.historico, name='historico_mapa'),
]