from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('usuarios', views.UserViewset)

urlpatterns = router.urls