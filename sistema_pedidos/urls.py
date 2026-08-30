from rest_framework.routers import DefaultRouter
from . import views
from django.urls import path

router = DefaultRouter()
router.register('clientes', views.ClienteViewSet)
router.register('pedidos', views.PedidoViewset)
router.register('item_pedido', views.ItemPedidoViewset)

urlpatterns = [
    path('aplicar-lista-a-todos/', views.aplicar_lista_a_todos, name='aplicar-lista-a-todos'),
    path('pedidos/nuevos/', views.pedidos_nuevos, name='pedidos_nuevos'),
    path('pedidos/facturar/', views.facturar_pedidos, name='facturar_pedidos'),
    path('clientes/buscar-xubio/', views.buscar_cliente_xubio, name='buscar_cliente_xubio'),
    path('catalogo/<str:token>/confirmar/', views.confirmar_pedido_catalogo, name='confirmar_pedido_catalogo'),
]+ router.urls