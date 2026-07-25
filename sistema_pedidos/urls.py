from rest_framework.routers import DefaultRouter
from . import views
from django.urls import path

router = DefaultRouter()
router.register('clientes', views.ClienteViewSet)
router.register('pedidos', views.PedidoViewset)
router.register('item_pedido', views.ItemPedidoViewset)

urlpatterns = [
    path('aplicar-lista-a-todos/', views.aplicar_lista_a_todos, name='aplicar-lista-a-todos')
]+ router.urls