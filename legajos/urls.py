from django.urls import path

from . import views

urlpatterns = [
    path("", views.legajos_view, name="legajos"),
    path("api/empleados/", views.api_empleados, name="legajos_api_empleados"),
    path("api/empleados/<int:pk>/", views.api_empleado_detail, name="legajos_api_empleado_detail"),
    path("api/documentacion/", views.api_documentacion, name="legajos_api_documentacion"),
    path("api/documentacion/<int:pk>/", views.api_documentacion_detail, name="legajos_api_documentacion_detail"),
    path("api/documentos/", views.api_documentos, name="legajos_api_documentos"),
    path("api/documentos/<int:pk>/firmar/", views.api_documento_firmar, name="legajos_api_documento_firmar"),
    path("api/ausencias/", views.api_ausencias, name="legajos_api_ausencias"),
    path("api/ausencias/<int:pk>/", views.api_ausencia_detail, name="legajos_api_ausencia_detail"),
    path("api/novedades/", views.api_novedades, name="legajos_api_novedades"),
    path("api/novedades/<int:pk>/", views.api_novedad_detail, name="legajos_api_novedad_detail"),
    path("api/cumpleanios/", views.api_cumpleanios, name="legajos_api_cumpleanios"),
]