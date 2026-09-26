from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase

from .models import Perfil


class NombrePerfilTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user('matiloinsta', password='x')
        Perfil.objects.create(usuario=self.admin, rol='admin', nombre='Mati')
        self.client.force_login(self.admin)

    def test_saludo_usa_el_nombre_del_perfil(self):
        html = self.client.get('/dashboard/').content.decode()
        self.assertIn('<em>Mati</em>', html)

    def test_sin_nombre_usa_el_usuario(self):
        self.admin.perfil.nombre = ''
        self.admin.perfil.save()
        html = self.client.get('/dashboard/').content.decode()
        self.assertIn('<em>matiloinsta</em>', html)

    def test_editar_nombre_por_api(self):
        otro = User.objects.create_user('nataliacarnero', password='x')
        Perfil.objects.create(usuario=otro, rol='colab')
        resp = self.client.patch(f'/api/users/usuarios/{otro.id}/', {'nombre': 'Nati'}, content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        otro.perfil.refresh_from_db()
        self.assertEqual(otro.perfil.nombre, 'Nati')
        self.assertEqual(otro.perfil.rol, 'colab')

    @mock.patch('users.utils.enviar_invitacion')
    def test_crear_usuario_con_nombre(self, _invitacion):
        resp = self.client.post('/api/users/usuarios/', {
            'username': 'juan', 'email': 'juan@example.com', 'rol': 'colab', 'nombre': 'Juancito',
        }, content_type='application/json')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(User.objects.get(username='juan').perfil.nombre, 'Juancito')

    def test_crear_usuario_sin_rol_falla(self):
        resp = self.client.post('/api/users/usuarios/', {'username': 'x', 'email': 'x@example.com'},
                                content_type='application/json')
        self.assertEqual(resp.status_code, 400)
