from django.shortcuts import render
from rest_framework import viewsets
from . import serializers, models
from .permissions import EsAdmin, EsColab, EsLector
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import User


# Create your views here.

class UserViewset(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = serializers.UserSerializer
    permission_classes = [EsAdmin]
