from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('clientes', views.ClienteViewSet)
router.register('pedidos', views.PedidoViewset)
router.register('item_pedido', views.ItemPedidoViewset)

urlpatterns = router.urls