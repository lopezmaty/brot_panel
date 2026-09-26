import io
import shutil
import tempfile
from datetime import datetime, timezone as dt_tz

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from notificaciones.models import Notificacion
from users.models import Perfil

from .models import ConfigHorario, Empleado, HistorialMes, MarcaFichada, RectificacionFichada

MEDIA_TMP = tempfile.mkdtemp()


def _marca(emp, y, m, d, hh, mm):
    return MarcaFichada.objects.create(empleado=emp, timestamp=datetime(y, m, d, hh, mm, tzinfo=dt_tz.utc), mes=f'{y}-{m:02d}')


def _foto():
    from PIL import Image
    buf = io.BytesIO()
    Image.new('RGB', (40, 60), 'white').save(buf, 'JPEG')
    return SimpleUploadedFile('formulario.jpg', buf.getvalue(), content_type='image/jpeg')


@override_settings(MEDIA_ROOT=MEDIA_TMP)
class RectificacionesTests(TestCase):
    API = '/api/control_horario/'

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TMP, ignore_errors=True)

    def setUp(self):
        self.admin = User.objects.create_user('ana')
        Perfil.objects.create(usuario=self.admin, rol='admin')
        self.colab = User.objects.create_user('beto')
        Perfil.objects.create(usuario=self.colab, rol='colab')
        self.lector = User.objects.create_user('ceci')
        Perfil.objects.create(usuario=self.lector, rol='read-only')

        self.emp = Empleado.objects.create(nombre='Perez Juan')
        # 3/9: sólo entrada y salida (se descuenta el descanso) → 9 h - 0,5 = 8,5 h
        _marca(self.emp, 2026, 9, 3, 6, 0)
        _marca(self.emp, 2026, 9, 3, 15, 0)
        self.client.force_login(self.admin)

    def _crear(self, fecha='2026-09-03', **extra):
        datos = {
            'empleado': 'Perez Juan', 'fecha': fecha, 'tipos': ['salida'], 'dni': '30.000.000',
            'real_entrada': '06:00', 'real_salida': '15:00',
            'motivo': 'Se olvidó de marcar la salida.', 'fecha_hora_aviso': '2026-09-04T09:00',
        }
        datos.update(extra)
        return self.client.post(self.API + 'rectificaciones/', datos, content_type='application/json')

    def _resolver(self, rid, **extra):
        datos = {'resolucion': 'acreditada', 'horario_corregido': '06:00 a 15:00 sin descanso',
                 'horas_a_liquidar': '9', 'aprobado_por': 'Encargado'}
        datos.update(extra)
        return self.client.post(f'{self.API}rectificaciones/{rid}/resolver/', datos, content_type='application/json')

    def _detalle(self):
        return self.client.get(self.API + 'detalle/?mes=2026-09').json()

    def test_flujo_completo_no_modifica_marcas(self):
        antes = list(MarcaFichada.objects.values_list('timestamp', flat=True))
        r = self._crear()
        self.assertEqual(r.status_code, 201)
        rid = r.json()['id']
        self.assertEqual(r.json()['estado'], 'pendiente_firma')
        self.assertEqual(r.json()['horas_provisionales'], 8.5)
        # 06:00 a 15:00 con el descanso de 30 min descontado
        self.assertEqual(r.json()['horas_declaradas'], 8.5)
        self.assertFalse(r.json()['fuera_de_termino'])

        # Sin foto no se puede resolver
        self.assertEqual(self._resolver(rid).status_code, 409)
        f = self.client.post(f'{self.API}rectificaciones/{rid}/foto/', {'foto': _foto()})
        self.assertEqual(f.json()['estado'], 'pendiente_resolucion')

        res = self._resolver(rid)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['impacto_horas'], 0.5)

        fila = next(x for x in self._detalle() if x['fecha'] == '2026-09-03')
        self.assertEqual(fila['a_liquidar'], 9.0)
        self.assertEqual(fila['a_liquidar_sistema'], 8.5)
        self.assertEqual(fila['h1'], '06:00:00')
        self.assertEqual(fila['h2'], '15:00:00')
        self.assertEqual(list(MarcaFichada.objects.values_list('timestamp', flat=True)), antes)

        resumen = self.client.get(self.API + 'resumen/?mes=2026-09').json()['resumenes'][0]
        self.assertEqual(resumen['total_horas_mes'], 9.0)
        self.assertEqual(resumen['incidencias'], 1)

    def test_no_acreditada_mantiene_calculo(self):
        rid = self._crear().json()['id']
        self.client.post(f'{self.API}rectificaciones/{rid}/foto/', {'foto': _foto()})
        res = self._resolver(rid, resolucion='no_acreditada')
        self.assertEqual(res.status_code, 200)
        self.assertIsNone(res.json()['horas_a_liquidar'])
        fila = next(x for x in self._detalle() if x['fecha'] == '2026-09-03')
        self.assertEqual(fila['a_liquidar'], 8.5)

    def test_dia_sin_marcas_aparece_y_suma_al_autorizarse(self):
        rid = self._crear(fecha='2026-09-05', tipos=['ingreso', 'salida']).json()['id']
        fila = next(x for x in self._detalle() if x['fecha'] == '2026-09-05')
        self.assertTrue(fila['sin_marcas'])
        self.assertEqual(fila['a_liquidar'], 0)
        self.client.post(f'{self.API}rectificaciones/{rid}/foto/', {'foto': _foto()})
        self._resolver(rid, horas_a_liquidar='8.5')
        fila = next(x for x in self._detalle() if x['fecha'] == '2026-09-05')
        self.assertEqual(fila['a_liquidar'], 8.5)

    def test_no_permite_duplicado_y_anular_libera_el_dia(self):
        rid = self._crear().json()['id']
        self.assertEqual(self._crear().status_code, 409)
        an = self.client.post(f'{self.API}rectificaciones/{rid}/anular/', {'motivo': 'Se cargó mal'}, content_type='application/json')
        self.assertEqual(an.json()['estado'], 'anulada')
        self.assertTrue(RectificacionFichada.objects.filter(pk=rid).exists())  # no se borra
        self.assertEqual(self._crear().status_code, 201)

    def test_mes_cerrado_bloquea_resolucion_y_pendientes_bloquean_cierre(self):
        rid = self._crear().json()['id']
        cierre = self.client.post(self.API + 'cerrar-mes/', {'mes': '2026-09'}, content_type='application/json')
        self.assertEqual(cierre.status_code, 409)
        self.client.post(f'{self.API}rectificaciones/{rid}/foto/', {'foto': _foto()})
        HistorialMes.objects.create(mes='2026-09', snapshot={})
        self.assertEqual(self._resolver(rid).status_code, 409)

    def test_solo_entrada_o_salida(self):
        # El descanso no se puede declarar: sólo marcas de entrada o salida
        self.assertEqual(self._crear(tipos=['descanso']).status_code, 400)
        r = self._crear(tipos=['descanso', 'salida'], sin_descanso_declarado=True, real_salida_descanso='10:00')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()['tipos'], ['salida'])
        self.assertFalse(r.json()['sin_descanso_declarado'])
        self.assertEqual(r.json()['real_salida_descanso'], '')

    def test_reporte_con_conformidad_sin_firma_de_empresa(self):
        from . import views_rectificaciones as vr
        from django.template.loader import render_to_string
        html = render_to_string('control_horario/reporte_mensual_pdf.html', vr.datos_reporte(self.emp, '2026-09'))
        self.assertIn('Acuerdo Individual Voluntario de Banco de Horas', html)
        self.assertNotIn('recibí copia', html)
        self.assertNotIn('Firma por BROTHAUS', html)

    def test_aviso_fuera_de_termino(self):
        r = self._crear(fecha_hora_aviso='2026-09-08T10:00')
        self.assertTrue(r.json()['fuera_de_termino'])

    def test_permisos(self):
        rid = self._crear().json()['id']
        self.client.post(f'{self.API}rectificaciones/{rid}/foto/', {'foto': _foto()})
        self.client.force_login(self.colab)
        self.assertEqual(self.client.get(self.API + 'rectificaciones/').status_code, 200)
        self.assertEqual(self._resolver(rid).status_code, 403)  # resolver: sólo admin
        self.client.force_login(self.lector)
        self.assertEqual(self.client.get(self.API + 'rectificaciones/').status_code, 403)

    def test_foto_invalida(self):
        rid = self._crear().json()['id']
        txt = SimpleUploadedFile('a.txt', b'hola', content_type='text/plain')
        self.assertEqual(self.client.post(f'{self.API}rectificaciones/{rid}/foto/', {'foto': txt}).status_code, 400)

    def test_limite_de_incidencias_notifica(self):
        ConfigHorario.objects.create(pk=1, limite_incidencias_mes=1)
        self._crear()
        self.assertTrue(Notificacion.objects.filter(titulo__contains='llegó a 1 incidencias').exists())

    def _legajo(self, nombre='Juan', apellido='Perez', dni='31222333', puesto='Panadero'):
        from datetime import date
        from legajos.models import Empleado as Legajo
        return Legajo.objects.create(nombre=nombre, apellido=apellido, dni=dni, puesto=puesto, fecha_ingreso=date(2024, 1, 1))

    def test_vincula_legajo_por_nombre_y_toma_dni_y_puesto(self):
        leg = self._legajo()
        self._legajo(nombre='Ana', apellido='Gomez', dni='40111222')  # no coincide
        data = self.client.get(self.API + 'rectificaciones/datos-dia/', {'empleado': 'Perez Juan', 'fecha': '2026-09-03'}).json()
        self.assertTrue(data['desde_legajo'])
        self.assertEqual(data['dni'], '31222333')
        self.assertEqual(data['sector_turno'], 'Panadero')
        self.assertEqual(data['empleado_display'], 'Juan Perez')
        self.emp.refresh_from_db()
        self.assertEqual(self.emp.legajo_id, leg.id)

        r = self._crear(dni='')
        self.assertEqual(r.json()['dni'], '31222333')
        legajos = self.client.get(self.API + 'legajos/').json()
        self.assertEqual({l['dni']: l['empleado_reloj'] for l in legajos}, {'31222333': 'Perez Juan', '40111222': None})

    def test_vincular_legajo_a_mano_y_no_duplicar(self):
        leg = self._legajo(nombre='Otro', apellido='Nombre', dni='1')
        otro = Empleado.objects.create(nombre='Gomez Ana')
        ok = self.client.post(self.API + 'empleados/update/', {'cambios': [{'id': self.emp.id, 'legajo_id': leg.id}]}, content_type='application/json')
        self.assertEqual(ok.status_code, 200)
        self.emp.refresh_from_db()
        self.assertEqual(self.emp.legajo_id, leg.id)
        dup = self.client.post(self.API + 'empleados/update/', {'cambios': [{'id': otro.id, 'legajo_id': leg.id}]}, content_type='application/json')
        self.assertEqual(dup.status_code, 409)

    def test_reporte_se_descarga_como_archivo(self):
        rep = self.client.get(self.API + 'reporte-mensual/', {'empleado': 'Perez Juan', 'mes': '2026-09'})
        self.assertTrue(rep['Content-Disposition'].startswith('attachment'))

    def test_pdfs(self):
        rid = self._crear().json()['id']
        anexo = self.client.get(f'{self.API}rectificaciones/{rid}/pdf/')
        self.assertEqual(anexo['Content-Type'], 'application/pdf')
        self.assertTrue(anexo.content.startswith(b'%PDF'))
        rep = self.client.get(self.API + 'reporte-mensual/', {'empleado': 'Perez Juan', 'mes': '2026-09'})
        self.assertEqual(rep['Content-Type'], 'application/pdf')
        self.assertTrue(rep.content.startswith(b'%PDF'))
