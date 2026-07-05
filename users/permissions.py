from rest_framework.permissions import BasePermission

class EsAdmin(BasePermission):
    def has_permission(self, request, view):
        try:
            return request.user.perfil.rol == 'admin'
        except AttributeError:
            return False
    
class EsColab(BasePermission):
    def has_permission(self, request, view):
        try:
            return request.user.perfil.rol == 'colab'
        except AttributeError:
            return False
        
class EsLector(BasePermission):
    def has_permission(self, request, view):
        try:
            return request.user.perfil.rol == 'read-only'
        except AttributeError:
            return False