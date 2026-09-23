from rest_framework.routers import DefaultRouter
from . import views
from django.urls import path

router = DefaultRouter()
router.register('clientes', views.ClienteViewSet)
router.register('pedidos', views.PedidoViewset)
router.register('item_pedido', views.ItemPedidoViewset)

urlpatterns = [
    path('pedidos/nuevos/', views.pedidos_nuevos, name='pedidos_nuevos'),
    path('pedidos/facturar/', views.facturar_pedidos, name='facturar_pedidos'),
    path('clientes/buscar-xubio/', views.buscar_cliente_xubio, name='buscar_cliente_xubio'),
    path('ventas-xubio-15dias/', views.ventas_xubio_15dias, name='ventas_xubio_15dias'),
    path('stock-productos/', views.stock_productos, name='stock_productos'),
    path('catalogo/<str:token>/comunicaciones/pendientes/', views.comunicaciones_pendientes_catalogo, name='comunicaciones_pendientes_catalogo'),
    path('catalogo/<str:token>/comunicaciones/<int:comunicacion_id>/confirmar/', views.confirmar_lectura_comunicacion, name='confirmar_lectura_comunicacion'),
] + router.urls