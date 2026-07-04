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