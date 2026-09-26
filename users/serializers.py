from rest_framework import serializers
from . import models
from django.contrib.auth.models import User
from . import utils

class UserSerializer(serializers.ModelSerializer):
    rol = serializers.ChoiceField(choices=models.Perfil.ROLES, write_only=True, required=False)
    rol_actual = serializers.CharField(source='perfil.rol', read_only=True)
    nombre = serializers.CharField(source='perfil.nombre', max_length=50, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'rol', 'rol_actual', 'nombre']

    def validate(self, attrs):
        if self.instance is None and not attrs.get('rol'):
            raise serializers.ValidationError({'rol': 'Este campo es requerido.'})
        return attrs

    def create(self, validated_data):
        rol = validated_data.pop('rol')
        nombre = validated_data.pop('perfil', {}).get('nombre', '')
        user = User.objects.create_user(**validated_data)
        user.set_unusable_password()
        user.save()
        models.Perfil.objects.create(usuario=user, rol=rol, nombre=nombre)
        utils.enviar_invitacion(user)

        return user

    def update(self, instance, validated_data):
        rol = validated_data.pop('rol', None)
        perfil_data = validated_data.pop('perfil', {})
        instance = super().update(instance, validated_data)
        perfil, _ = models.Perfil.objects.get_or_create(usuario=instance, defaults={'rol': rol or 'read-only'})
        if rol:
            perfil.rol = rol
        if 'nombre' in perfil_data:
            perfil.nombre = perfil_data['nombre']
        perfil.save()
        return instance
