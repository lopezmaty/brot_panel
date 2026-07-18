from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('lista-precios/', views.lista_precios_view, name='lista_precios'),
    path('clientes/', views.clientes_view, name='clientes'),
    path('pedidos/', views.centro_pedidos_view, name='centro_pedidos'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('usuarios/', views.usuarios_view, name='usuarios'),
    path('establecer-password/<uid>/<token>/', views.establecer_password_view, name='establecer_password')
]