from rest_framework.routers import DefaultRouter
from . import views
from django.urls import path

router = DefaultRouter()
router.register('productos', views.ProductoViewset)
router.register('variedades', views.VariedadViewset)
router.register('tamaño', views.TamañoViewset)
router.register('familia', views.FamiliaViewset)
router.register('lista_precios', views.ListaPreciosViewset)
router.register('precios', views.PreciosViewset)
router.register('tipo_cliente', views.TipoClienteViewset)

urlpatterns = [
    path('guardar-lista-completa/', views.guardar_lista_completa, name='guardar-lista-completa')
] + router.urls