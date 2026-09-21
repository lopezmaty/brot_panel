from django.db import transaction
from django.utils import timezone

from . import models


def aplicar_actualizaciones_pendientes(lista=None):
    """Vuelca a Precio las actualizaciones programadas cuya vigencia ya llegó.
    Si se pasa una lista, solo procesa esa. Es seguro llamarla muchas veces."""
    pendientes = models.ActualizacionPrecios.objects.filter(
        estado='programada',
        vigente_desde__lte=timezone.now(),
    )
    if lista is not None:
        pendientes = pendientes.filter(lista_precio=lista)

    for actualizacion_id in list(pendientes.values_list('id', flat=True)):
        _aplicar(actualizacion_id)


def _aplicar(actualizacion_id):
    with transaction.atomic():
        # Bloquea la fila: si dos requests llegan a la vez, solo uno aplica
        actualizacion = (
            models.ActualizacionPrecios.objects
            .select_for_update()
            .get(pk=actualizacion_id)
        )
        if actualizacion.estado != 'programada':
            return

        for item in actualizacion.items.select_related('producto'):
            models.Precio.objects.update_or_create(
                lista_precio=actualizacion.lista_precio,
                producto=item.producto,
                defaults={'precio': item.precio_nuevo},
            )
            models.HistorialPrecio.objects.create(
                lista_precio=actualizacion.lista_precio,
                producto=item.producto,
                precio=item.precio_nuevo,
            )

        actualizacion.estado = 'aplicada'
        actualizacion.aplicada_en = timezone.now()
        actualizacion.save(update_fields=['estado', 'aplicada_en'])