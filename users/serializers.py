from rest_framework import serializers
from . import models
from django.contrib.auth.models import User

class UserSerializer(serializers.ModelSerializer):
    rol = serializers.CharField(write_only=True)
    rol_actual = serializers.CharField(source='perfil.rol', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'rol', 'rol_actual']

    def create(self, validated_data):
        rol = validated_data.pop('rol')
        user = User.objects.create_user(**validated_data)
        user.set_unusable_password()
        user.save()
        models.Perfil.objects.create(usuario=user, rol= rol)

        return user
        


    