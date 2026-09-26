from django.urls import path

from . import views

urlpatterns = [
    path('', views.listar, name='notificaciones_listar'),
    path('leer-todas/', views.marcar_todas, name='notificaciones_leer_todas'),
    path('<int:notificacion_id>/leer/', views.marcar_leida, name='notificaciones_leer'),
]
