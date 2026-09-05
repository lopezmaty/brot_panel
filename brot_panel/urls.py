"""
URL configuration for brot_panel project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from frontend.views import catalogo_view, perfil_catalogo_view
from sistema_pedidos.views import confirmar_pedido_catalogo
from django.conf import settings
from django.conf.urls.static import static
from frontend.views import catalogo_view, perfil_catalogo_view
from gestion_gerencial.views import mapa_economico_view, costeo_precios_view


urlpatterns = [
    path('', RedirectView.as_view(url='/login/', permanent=False)),
    path('admin/', admin.site.urls),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/lista_precios/', include('lista_precios.urls')),
    path('api/sistema_pedidos/', include('sistema_pedidos.urls')),
    path('', include('frontend.urls')),
    path('api/users/', include('users.urls')),
    path('catalogo/<str:token>/perfil/', perfil_catalogo_view, name='perfil_catalogo'),
    path('catalogo/<str:token>/confirmar/', confirmar_pedido_catalogo, name='confirmar_pedido_catalogo'),
    path('catalogo/<str:token>/', catalogo_view, name='catalogo'),
    path('api/gestion_gerencial/', include('gestion_gerencial.urls')),
    path('gestion-gerencial/mapa-economico/', mapa_economico_view, name='mapa_economico'),
    path('gestion-gerencial/costeo-precios/', costeo_precios_view, name='costeo_precios'),
    
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)