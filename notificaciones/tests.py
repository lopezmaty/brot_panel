from datetime import date, timedelta
from decimal import Decimal
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from users.models import Perfil

from .models import Notificacion
from .services import notificar


class NotificacionesTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user('ana', password='x')
        Perfil.objects.create(usuario=self.admin, rol='admin')
        self.colab = User.objects.create_user('beto', password='x')
        Perfil.objects.create(usuario=self.colab, rol='colab')

    def test_destinatarios(self):
        notificar('Para todos')
        notificar('Sólo admins', rol='admin')
        notificar('Sólo Beto', usuario=self.colab)

        titulos_admin = set(Notificacion.objects.para_usuario(self.admin).values_list('titulo', flat=True))
        titulos_colab = set(Notificacion.objects.para_usuario(self.colab).values_list('titulo', flat=True))
        self.assertEqual(titulos_admin, {'Para todos', 'Sólo admins'})
        self.assertEqual(titulos_colab, {'Para todos', 'Sólo Beto'})

    def test_listar_y_marcar_leidas(self):
        n = notificar('Nuevo pedido', url='/pedidos/')
        notificar('Otra')
        self.client.force_login(self.admin)

        data = self.client.get('/notificaciones/').json()
        self.assertEqual(data['no_leidas'], 2)

        self.client.post(f'/notificaciones/{n.id}/leer/')
        self.assertEqual(self.client.get('/notificaciones/').json()['no_leidas'], 1)

        self.client.post('/notificaciones/leer-todas/')
        self.assertEqual(self.client.get('/notificaciones/').json()['no_leidas'], 0)
        # Leer no afecta a otros usuarios
        self.client.force_login(self.colab)
        self.assertEqual(self.client.get('/notificaciones/').json()['no_leidas'], 2)

    def test_no_puede_leer_notificacion_ajena(self):
        n = notificar('Privada', usuario=self.colab)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.post(f'/notificaciones/{n.id}/leer/').status_code, 404)

    def test_requiere_login(self):
        self.assertEqual(self.client.get('/notificaciones/').status_code, 302)


class DashboardWidgetsTests(TestCase):
    def test_widgets_del_dia(self):
        from lista_precios.models import Familia, Producto, Tamaño, TipoCliente, Variedad
        from sistema_pedidos.models import Cliente, ItemPedido, Pedido

        user = User.objects.create_user('ana', password='x')
        Perfil.objects.create(usuario=user, rol='admin')
        tipo = TipoCliente.objects.create(nombre='Gastronómico')
        cliente = Cliente.objects.create(
            nombre='A', razon_social='A SA', cuit='1', nombre_comercio='A', direccion='x', ciudad='x',
            provincia='x', telefono='1', mail='a@a.com', condicion_iva='consumidor_final', tipo_cliente=tipo,
        )
        producto = Producto.objects.create(
            nombre='Burger Bun', variedad=Variedad.objects.create(nombre='Brioche'),
            tamaño=Tamaño.objects.create(nombre='Chico'), tipo_medida=Producto.TIPO_MEDIDA[0][0],
            familia=Familia.objects.create(nombre='Hamburguesa'), unidades_paquete=6,
        )

        p1 = Pedido.objects.create(cliente=cliente, metodo_entrega='retiro')
        ItemPedido.objects.create(pedido=p1, producto=producto, cantidad=10, precio=Decimal('100'))
        cancelado = Pedido.objects.create(cliente=cliente, metodo_entrega='retiro', estado='cancelado')
        ItemPedido.objects.create(pedido=cancelado, producto=producto, cantidad=99, precio=Decimal('1'))

        # Un pedido nuevo de hace 10 días también cuenta como "nuevo" (pero no suma a las ventas de hoy)
        viejo = Pedido.objects.create(cliente=cliente, metodo_entrega='retiro')
        ItemPedido.objects.create(pedido=viejo, producto=producto, cantidad=5, precio=Decimal('100'))
        Pedido.objects.filter(pk=viejo.pk).update(fecha=p1.fecha - timedelta(days=10))
        # Un pedido ya confirmado no cuenta como nuevo
        Pedido.objects.create(cliente=cliente, metodo_entrega='retiro', estado='en_proceso')

        self.client.force_login(user)
        with mock.patch('django.utils.timezone.localdate', return_value=timezone.localtime(p1.fecha).date()):
            w = self.client.get('/dashboard/').context['widgets']
        self.assertEqual(w['pedidos_nuevos'], 2)
        self.assertEqual(w['pedidos_nuevos_hoy'], 1)
        self.assertEqual(w['unidades_hoy'], 10)
        self.assertEqual(w['ventas_hoy'], 1000.0)

    def test_dashboard_carga_sin_datos(self):
        user = User.objects.create_user('ana', password='x')
        self.client.force_login(user)
        with mock.patch('django.utils.timezone.localdate', return_value=date(2026, 1, 1)):
            resp = self.client.get('/dashboard/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['widgets']['pedidos_nuevos'], 0)
