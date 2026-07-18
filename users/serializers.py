from rest_framework import serializers
from . import models
from django.contrib.auth.models import User

class UserSerializer(serializers.ModelSerializer):
    rol = serializers.SerializerMethodField()

    def get_rol(self, obj):
            return obj.perfil.rol
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'rol']


    