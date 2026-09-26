from django.conf import settings
from django.db import models
from django.db.models import Q


class NotificacionQuerySet(models.QuerySet):
    def para_usuario(self, usuario):
        """Notificaciones que le corresponden a un usuario: las dirigidas a él,
        las de su rol y las generales (sin usuario ni rol)."""
        rol = getattr(getattr(usuario, 'perfil', None), 'rol', None)
        filtro = Q(usuario=usuario) | Q(usuario__isnull=True, rol='')
        if rol:
            filtro |= Q(usuario__isnull=True, rol=rol)
        return self.filter(filtro)


class Notificacion(models.Model):
    """Aviso que aparece en la campanita del panel.

    Se crea desde cualquier módulo con notificaciones.services.notificar().
    Si no tiene usuario ni rol, la ven todos los usuarios del panel.
    """

    NIVELES = [
        ('info', 'Información'),
        ('exito', 'Éxito'),
        ('alerta', 'Alerta'),
        ('error', 'Error'),
    ]

    titulo = models.CharField(max_length=120)
    mensaje = models.CharField(max_length=300, blank=True)
    url = models.CharField(max_length=300, blank=True, help_text='Adónde lleva al hacer clic (opcional).')
    icono = models.CharField(max_length=50, default='ti-bell', help_text='Nombre de ícono de Tabler, ej: ti-clipboard-list.')
    nivel = models.CharField(max_length=10, choices=NIVELES, default='info')
    modulo = models.CharField(max_length=50, blank=True, help_text='Módulo que la generó, ej: pedidos.')

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        null=True, blank=True, related_name='notificaciones',
        help_text='Si se completa, sólo la ve este usuario.',
    )
    rol = models.CharField(max_length=50, blank=True, help_text='Si se completa, sólo la ven los usuarios con este rol.')

    leida_por = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='notificaciones_leidas')
    creada = models.DateTimeField(auto_now_add=True)

    objects = NotificacionQuerySet.as_manager()

    class Meta:
        ordering = ['-creada']
        verbose_name = 'notificación'
        verbose_name_plural = 'notificaciones'

    def __str__(self):
        return self.titulo
