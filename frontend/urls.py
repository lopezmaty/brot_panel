from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('clientes/', views.clientes_view, name='clientes'),
    path('clientes/nuevo/', views.cliente_detalle_view, name='cliente_nuevo'),
    path('clientes/<cliente_id>/', views.cliente_detalle_view, name='cliente_editar'),
    path('pedidos/', views.centro_pedidos_view, name='centro_pedidos'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('usuarios/', views.usuarios_view, name='usuarios'),
    path('establecer-password/<uid>/<token>/', views.establecer_password_view, name='establecer_password'),
    path('producto/', views.producto_view, name='producto'),
    path('producto/nuevo/', views.producto_detalle_view, name='producto_nuevo'),
    path('producto/<producto_id>/', views.producto_detalle_view, name='producto_editar'),
    path('lista_precios/', views.lista_precios_view, name='lista_precios'),
    path('lista_precios/nuevo/', views.lista_precios_detalle_view, name='lista_precios_nuevo'),
    path('lista_precios/<lista_precios_id>/', views.lista_precios_detalle_view, name='lista_precios_editar'), 
]