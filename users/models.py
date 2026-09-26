from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class Perfil(models.Model):
    ROLES = [
        ('admin', 'administrativo'),
        ('colab', 'colaborador'),
        ('read-only', 'lector')
    ]

    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    rol = models.CharField(max_length=50, choices=ROLES)
    nombre = models.CharField(max_length=50, blank=True, help_text='Cómo se muestra en el panel, ej: "Mati".')

    @property
    def nombre_visible(self):
        return self.nombre or self.usuario.first_name or self.usuario.username

    def __str__(self):
        return self.usuario.username