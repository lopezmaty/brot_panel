from django.urls import path
from . import views, views_flujo

urlpatterns = [
    # --- Mapa Económico ---
    path('importar-compras-xubio/', views.importar_compras_xubio, name='importar_compras_xubio_mapa'),
    path('importar-ventas-xubio/', views.importar_ventas_xubio, name='importar_ventas_xubio_mapa'),
    path('compras/', views.listar_compras_mes, name='listar_compras_mes'),
    path('asignar-rubro-compra/', views.asignar_rubro_compra, name='asignar_rubro_compra'),
    path('datos-mes/', views.obtener_datos_mes, name='obtener_datos_mes'),
    path('guardar-datos-mes/', views.guardar_datos_mes, name='guardar_datos_mes'),
    path('ventas-detalle/', views.ventas_detalle_mes, name='ventas_detalle_mes'),
    path('dashboard-mes/', views.dashboard_mes, name='dashboard_mes_mapa'),
    path('historico/', views.historico, name='historico_mapa'),

    # --- Centro de Costos ---
    path('costeo/importar-precios/', views.importar_precios_costeo, name='importar_precios_costeo'),
    path('costeo/calculos/', views.costeo_calculos, name='costeo_calculos'),
    path('costeo/productos/', views.costeo_productos, name='costeo_productos'),
    path('costeo/productos/bulk-update/', views.costeo_productos_bulk_update, name='costeo_productos_bulk_update'),
    path('costeo/insumos/', views.costeo_insumos, name='costeo_insumos'),
    path('costeo/insumos/bulk-update/', views.costeo_insumos_bulk_update, name='costeo_insumos_bulk_update'),
    path('costeo/config/', views.costeo_config, name='costeo_config'),
    path('costeo/equipos/', views.costeo_equipos, name='costeo_equipos'),
    path('costeo/equipos/bulk-update/', views.costeo_equipos_bulk_update, name='costeo_equipos_bulk_update'),
    path('costeo/historial/', views.costeo_historial, name='costeo_historial'),
    path('costeo/mano-obra/bulk-update/', views.costeo_mano_obra_bulk_update, name='costeo_mano_obra_bulk_update'),
    path('costeo/recetas/guardar/', views.costeo_recetas_guardar, name='costeo_recetas_guardar'),
    path('costeo/cerrar-mes/', views.cerrar_mes_costeo, name='cerrar_mes_costeo'),
    path('costeo/cierres/', views.listar_cierres_costeo, name='listar_cierres_costeo'),
    path('costeo/cierre/', views.obtener_cierre_costeo, name='obtener_cierre_costeo'),

    # --- Estado de Resultados (EERR) ---
    path('eerr/importar-compras/', views.importar_compras_eerr, name='importar_compras_eerr'),
    path('eerr/importar-ventas/', views.importar_ventas_eerr, name='importar_ventas_eerr'),
    path('eerr/compras/', views.listar_compras_eerr, name='listar_compras_eerr'),
    path('eerr/asignar-cuenta-compra/', views.asignar_cuenta_compra_eerr, name='asignar_cuenta_compra_eerr'),
    path('eerr/plan-cuentas/', views.plan_cuentas_eerr, name='plan_cuentas_eerr'),
    path('eerr/ventas/', views.ventas_eerr_mes, name='ventas_eerr_mes'),
    path('eerr/mapeos-producto-costeo/', views.mapeos_producto_costeo, name='mapeos_producto_costeo'),
    path('eerr/asignar-mapeo-producto-costeo/', views.asignar_mapeo_producto_costeo, name='asignar_mapeo_producto_costeo'),
    path('eerr/calcular/', views.calcular_eerr_mes, name='calcular_eerr_mes'),
    path('eerr/historico/', views.historico_eerr, name='historico_eerr'),

    # --- Presupuesto EERR ---
    path('presupuesto/', views.presupuesto_eerr, name='presupuesto_eerr'),
    path('presupuesto/guardar/', views.guardar_presupuesto_eerr, name='guardar_presupuesto_eerr'),

    # --- Flujo de fondos ---
    path('flujo-fondos/resumen/', views_flujo.ff_resumen, name='ff_resumen'),
    path('flujo-fondos/cuentas/', views_flujo.ff_cuentas, name='ff_cuentas'),
    path('flujo-fondos/cuentas/<int:pk>/', views_flujo.ff_cuenta_detalle, name='ff_cuenta_detalle'),
    path('flujo-fondos/cuentas/<int:pk>/saldar/', views_flujo.ff_cuenta_saldar, name='ff_cuenta_saldar'),
    path('flujo-fondos/importar/', views_flujo.ff_importar, name='ff_importar'),
    path('flujo-fondos/saldos/', views_flujo.ff_saldos, name='ff_saldos'),
    path('flujo-fondos/saldos/<int:pk>/', views_flujo.ff_saldo_detalle, name='ff_saldo_detalle'),
]