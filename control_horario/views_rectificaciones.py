"""API de rectificaciones de fichada (Anexo I) y reporte mensual por empleado."""
import base64
import mimetypes
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from functools import lru_cache

from django.contrib.staticfiles import finders
from django.db import transaction
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.utils import timezone
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from notificaciones.services import notificar

from . import models
from . import rectificaciones as rects
from .legajos_link import datos_legajo, vincular_automaticamente
from .views import _ajustes_dict, _errores_manuales_set, _mes_cerrado, build_detalle, monthly_summary

R = models.RectificacionFichada
MAX_FOTO_MB = 12
DIAS = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto',
         'septiembre', 'octubre', 'noviembre', 'diciembre']


class EsAdminOColab(BasePermission):
    def has_permission(self, request, view):
        rol = getattr(getattr(request.user, 'perfil', None), 'rol', None)
        return rol in ('admin', 'colab')


class EsAdmin(BasePermission):
    def has_permission(self, request, view):
        return getattr(getattr(request.user, 'perfil', None), 'rol', None) == 'admin'


# ── Helpers ──────────────────────────────────────────────────────────────────

def _usuario(u):
    if not u:
        return ''
    perfil = getattr(u, 'perfil', None)
    return (getattr(perfil, 'nombre', '') or u.get_full_name() or u.username)


def _hora(valor):
    if not valor:
        return None
    try:
        return time.fromisoformat(str(valor)[:5])
    except ValueError:
        return None


def _decimal(valor):
    if valor in (None, ''):
        return None
    try:
        return Decimal(str(valor).replace(',', '.')).quantize(Decimal('0.01'))
    except InvalidOperation:
        return None


def _bool_o_none(valor):
    if valor in (True, 'si', 'true', '1', 1):
        return True
    if valor in (False, 'no', 'false', '0', 0):
        return False
    return None


def _fila_del_dia(empleado, fecha):
    """Fila del detalle diario tal como la calcula el sistema (sin rectificación)."""
    qs = models.MarcaFichada.objects.filter(empleado=empleado, mes=fecha.strftime('%Y-%m')).select_related('empleado')
    for fila in build_detalle(qs, _errores_manuales_set(fecha.strftime('%Y-%m'))):
        if fila['fecha'] == fecha.isoformat():
            return fila
    return None


def serializar(r):
    t = lambda v: v.strftime('%H:%M') if v else ''
    return {
        'id': r.id,
        'numero': r.numero,
        'empleado': r.empleado.nombre,
        'empleado_display': datos_legajo(r.empleado)['nombre_completo'],
        'fecha': r.fecha.isoformat(),
        'mes': r.fecha.strftime('%Y-%m'),
        'estado': r.estado,
        'estado_label': r.get_estado_display(),
        'dni': r.dni,
        'sector_turno': r.sector_turno,
        'tipos': r.tipos,
        'tipos_label': [rects.TIPOS_LABEL.get(x, x) for x in r.tipos],
        'tipo_otro': r.tipo_otro,
        'marcas_originales': r.marcas_originales,
        'calculo_provisional': r.calculo_provisional,
        'horas_provisionales': float(r.horas_provisionales),
        'real_entrada': t(r.real_entrada),
        'real_salida_descanso': t(r.real_salida_descanso),
        'real_regreso_descanso': t(r.real_regreso_descanso),
        'real_salida': t(r.real_salida),
        'sin_descanso_declarado': r.sin_descanso_declarado,
        'horas_declaradas': rects.horas_declaradas(r.real_entrada, r.real_salida_descanso, r.real_regreso_descanso,
                                                   r.real_salida, r.empleado, r.sin_descanso_declarado),
        'horario_real_texto': r.horario_real_texto,
        'motivo': r.motivo,
        'fecha_hora_aviso': timezone.localtime(r.fecha_hora_aviso).strftime('%Y-%m-%dT%H:%M'),
        'medio_aviso': r.medio_aviso,
        'fuera_de_termino': r.aviso_fuera_de_termino,
        'creada_por': _usuario(r.creada_por),
        'creada_el': timezone.localtime(r.creada_el).isoformat(),
        'tiene_foto': bool(r.foto),
        'foto_url': f'/api/control_horario/rectificaciones/{r.id}/foto/' if r.foto else None,
        'foto_es_pdf': bool(r.foto and r.foto.name.lower().endswith('.pdf')),
        'foto_subida_el': timezone.localtime(r.foto_subida_el).isoformat() if r.foto_subida_el else None,
        'verif_biometrico': r.verif_biometrico,
        'verif_horario_programado': r.verif_horario_programado,
        'verif_camaras': r.verif_camaras,
        'verif_registros': r.verif_registros,
        'verif_supervisor': r.verif_supervisor,
        'verif_otros': r.verif_otros,
        'resolucion': r.resolucion,
        'resolucion_label': r.get_resolucion_display() if r.resolucion else '',
        'horario_corregido': r.horario_corregido,
        'horas_a_liquidar': float(r.horas_a_liquidar) if r.horas_a_liquidar is not None else None,
        'impacto_horas': round(float(r.horas_a_liquidar) - float(r.horas_provisionales), 2) if r.autoriza_correccion else 0,
        'observaciones': r.observaciones,
        'aprobado_por': r.aprobado_por,
        'resuelta_por': _usuario(r.resuelta_por),
        'resuelta_el': timezone.localtime(r.resuelta_el).isoformat() if r.resuelta_el else None,
        'motivo_anulacion': r.motivo_anulacion,
        'pdf_url': f'/api/control_horario/rectificaciones/{r.id}/pdf/',
    }


@lru_cache(maxsize=1)
def _logo_base64():
    path = finders.find('img/logo_Brot.png') or finders.find('img/logo.png')
    if not path:
        return None
    with open(path, 'rb') as f:
        return base64.b64encode(f.read()).decode('ascii')


def _pdf(template, contexto, nombre_archivo):
    from weasyprint import HTML
    contexto = {**contexto, 'logo_base64': _logo_base64(), 'emitido_el': timezone.localtime()}
    pdf = HTML(string=render_to_string(template, contexto)).write_pdf()
    resp = HttpResponse(pdf, content_type='application/pdf')
    resp['Content-Disposition'] = f'inline; filename="{nombre_archivo}"'
    return resp


# ── Datos del día (para precargar el formulario) ─────────────────────────────

@api_view(['GET'])
@permission_classes([EsAdminOColab])
def datos_dia(request):
    vincular_automaticamente()
    emp = get_object_or_404(models.Empleado.objects.select_related('legajo'), nombre=request.GET.get('empleado'))
    leg = datos_legajo(emp)
    try:
        fecha = date.fromisoformat(request.GET.get('fecha', ''))
    except ValueError:
        return Response({'error': 'Fecha inválida.'}, status=400)
    fila = _fila_del_dia(emp, fecha)
    existente = rects.rectificaciones_qs(empleado=emp).filter(fecha=fecha).first()
    return Response({
        'empleado': emp.nombre,
        'empleado_display': leg['nombre_completo'],
        'dni': leg['dni'],
        'sector_turno': leg['puesto'],
        'desde_legajo': leg['desde_legajo'],
        'medio_jornada': emp.medio_jornada,
        'sin_descuento_descanso': emp.sin_descuento_descanso,
        'marcas': [fila.get(k) for k in ('h1', 'h2', 'h3', 'h4')] if fila else [],
        'marcas_originales': rects.formatear_marcas(fila),
        'calculo_provisional': rects.formatear_calculo(fila),
        'horas_provisionales': round(fila['a_liquidar'], 2) if fila else 0,
        'rectificacion_existente': serializar(existente) if existente else None,
        'mes_cerrado': _mes_cerrado(fecha.strftime('%Y-%m')),
    })


# ── Listado y alta ───────────────────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([EsAdminOColab])
def rectificaciones(request):
    if request.method == 'GET':
        qs = R.objects.select_related('empleado', 'creada_por', 'resuelta_por', 'foto_subida_por')
        mes = request.GET.get('mes')
        if mes:
            y, m = [int(x) for x in mes.split('-')]
            qs = qs.filter(fecha__year=y, fecha__month=m)
        if request.GET.get('empleado'):
            qs = qs.filter(empleado__nombre=request.GET['empleado'])
        if request.GET.get('estado'):
            qs = qs.filter(estado=request.GET['estado'])
        return Response([serializar(r) for r in qs])

    d = request.data
    emp = models.Empleado.objects.filter(nombre=d.get('empleado')).first()
    if not emp:
        return Response({'error': 'Empleado no encontrado.'}, status=404)
    try:
        fecha = date.fromisoformat(d.get('fecha', ''))
    except ValueError:
        return Response({'error': 'Fecha de la incidencia inválida.'}, status=400)
    if fecha > timezone.localdate():
        return Response({'error': 'La fecha de la incidencia no puede ser futura.'}, status=400)
    if not (d.get('motivo') or '').strip():
        return Response({'error': 'Completá el motivo de la incidencia.'}, status=400)
    # Sólo se rectifican marcas de entrada o salida (el descanso no se declara)
    tipos = [t for t in (d.get('tipos') or []) if t in rects.TIPOS_PERMITIDOS]
    if not tipos:
        return Response({'error': 'Elegí si la incidencia es de entrada o de salida.'}, status=400)
    if rects.rectificaciones_qs(empleado=emp).filter(fecha=fecha).exists():
        return Response({'error': 'Ya hay una rectificación activa para ese empleado y día. Anulala si necesitás cargar otra.'}, status=409)

    try:
        aviso = datetime.fromisoformat(d.get('fecha_hora_aviso')) if d.get('fecha_hora_aviso') else None
    except ValueError:
        aviso = None
    aviso = timezone.make_aware(aviso) if aviso and timezone.is_naive(aviso) else (aviso or timezone.now())

    fila = _fila_del_dia(emp, fecha)
    with transaction.atomic():
        r = R.objects.create(
            empleado=emp,
            fecha=fecha,
            dni=(d.get('dni') or '').strip() or datos_legajo(emp)['dni'],
            sector_turno=(d.get('sector_turno') or '').strip() or datos_legajo(emp)['puesto'],
            tipos=tipos,
            tipo_otro='',
            marcas_originales=rects.formatear_marcas(fila),
            calculo_provisional=rects.formatear_calculo(fila),
            horas_provisionales=Decimal(str(round(fila['a_liquidar'], 2))) if fila else Decimal('0'),
            real_entrada=_hora(d.get('real_entrada')),
            real_salida=_hora(d.get('real_salida')),
            horario_real_texto=(d.get('horario_real_texto') or '').strip(),
            motivo=d['motivo'].strip(),
            fecha_hora_aviso=aviso,
            medio_aviso=(d.get('medio_aviso') or R._meta.get_field('medio_aviso').default).strip(),
            creada_por=request.user,
        )
        # Recordar DNI y sector para la próxima vez (si no vienen del legajo)
        cambios = []
        if r.dni and emp.dni != r.dni and not emp.legajo_id:
            emp.dni = r.dni
            cambios.append('dni')
        if r.sector_turno and emp.sector_turno != r.sector_turno:
            emp.sector_turno = r.sector_turno
            cambios.append('sector_turno')
        if cambios:
            emp.save(update_fields=cambios)

    _avisar_alta(r)
    return Response(serializar(r), status=201)


def _avisar_alta(r):
    try:
        notificar(
            f'Rectificación N° {r.numero} pendiente de firma',
            f'{r.empleado.nombre_display()} · {r.fecha:%d/%m/%Y}. Imprimí el Anexo I y subí la foto firmada.',
            url='/administracion/control-horario/', icono='ti-clock-edit', nivel='alerta',
            modulo='control_horario', rol='admin',
        )
        limite = models.ConfigHorario.actual().limite_incidencias_mes
        cantidad = rects.incidencias_por_empleado(r.fecha.strftime('%Y-%m')).get(r.empleado.nombre, 0)
        if limite and cantidad == limite:
            notificar(
                f'{r.empleado.nombre_display()} llegó a {cantidad} incidencias',
                f'En {MESES[r.fecha.month - 1]} alcanzó el límite configurado. Evaluar apercibimiento (no es automático).',
                url='/administracion/control-horario/', icono='ti-alert-triangle', nivel='error',
                modulo='control_horario', rol='admin',
            )
    except Exception:
        # Las notificaciones nunca deben impedir registrar la rectificación
        pass


@api_view(['GET'])
@permission_classes([EsAdminOColab])
def rectificacion_detalle(request, rect_id):
    return Response(serializar(get_object_or_404(R, pk=rect_id)))


# ── PDF del Anexo I ──────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([EsAdminOColab])
def rectificacion_pdf(request, rect_id):
    r = get_object_or_404(R.objects.select_related('empleado', 'resuelta_por'), pk=rect_id)
    return _pdf('control_horario/anexo_i_pdf.html', {'r': r, 'd': serializar(r)},
                f'Anexo_I_{r.numero}_{r.empleado.nombre.replace(" ", "_")}.pdf')


# ── Foto del formulario firmado ──────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([EsAdminOColab])
@parser_classes([MultiPartParser, FormParser])
def rectificacion_foto(request, rect_id):
    r = get_object_or_404(R, pk=rect_id)
    if request.method == 'GET':
        if not r.foto:
            return Response({'error': 'Todavía no se subió la foto.'}, status=404)
        tipo = mimetypes.guess_type(r.foto.name)[0] or 'application/octet-stream'
        return FileResponse(r.foto.open('rb'), content_type=tipo)

    if r.estado == R.Estado.ANULADA:
        return Response({'error': 'La rectificación está anulada.'}, status=409)
    archivo = request.FILES.get('foto')
    if not archivo:
        return Response({'error': 'Elegí la foto del formulario firmado.'}, status=400)
    tipo = (archivo.content_type or '').lower()
    if not (tipo.startswith('image/') or tipo == 'application/pdf'):
        return Response({'error': 'El archivo tiene que ser una foto (JPG, PNG, HEIC) o un PDF.'}, status=400)
    if archivo.size > MAX_FOTO_MB * 1024 * 1024:
        return Response({'error': f'El archivo supera los {MAX_FOTO_MB} MB.'}, status=400)

    extension = (archivo.name.rsplit('.', 1)[-1] if '.' in archivo.name else 'jpg').lower()
    archivo.name = f'rectificacion_{r.numero}_{r.fecha:%Y%m%d}.{extension}'
    r.foto = archivo
    r.foto_subida_el = timezone.now()
    r.foto_subida_por = request.user
    if r.estado == R.Estado.PENDIENTE_FIRMA:
        r.estado = R.Estado.PENDIENTE_RESOLUCION
    r.save()
    return Response(serializar(r))


# ── Parte 2: verificación y resolución ───────────────────────────────────────

@api_view(['POST'])
@permission_classes([EsAdmin])
def rectificacion_resolver(request, rect_id):
    r = get_object_or_404(R, pk=rect_id)
    d = request.data
    if r.estado == R.Estado.ANULADA:
        return Response({'error': 'La rectificación está anulada.'}, status=409)
    if not r.foto:
        return Response({'error': 'Primero subí la foto del formulario firmado.'}, status=409)
    if _mes_cerrado(r.fecha.strftime('%Y-%m')):
        return Response({'error': 'El mes de la incidencia está cerrado. Un administrador tiene que abrirlo para registrar la resolución.'}, status=409)

    resolucion = d.get('resolucion')
    if resolucion not in R.Resolucion.values:
        return Response({'error': 'Elegí la resolución.'}, status=400)
    horas = _decimal(d.get('horas_a_liquidar'))
    if resolucion != R.Resolucion.NO_ACREDITADA:
        if horas is None or horas < 0 or horas > 24:
            return Response({'error': 'Indicá las horas a liquidar de ese día (entre 0 y 24).'}, status=400)
        if not (d.get('horario_corregido') or '').strip():
            return Response({'error': 'Indicá el horario corregido.'}, status=400)
    else:
        horas = None
    if not (d.get('aprobado_por') or '').strip():
        return Response({'error': 'Indicá quién aprobó (el responsable que firmó).'}, status=400)

    r.verif_biometrico = _bool_o_none(d.get('verif_biometrico'))
    r.verif_horario_programado = _bool_o_none(d.get('verif_horario_programado'))
    r.verif_camaras = d.get('verif_camaras') if d.get('verif_camaras') in dict(R.CAMARAS) else ''
    r.verif_registros = _bool_o_none(d.get('verif_registros'))
    r.verif_supervisor = _bool_o_none(d.get('verif_supervisor'))
    r.verif_otros = (d.get('verif_otros') or '').strip()
    r.resolucion = resolucion
    r.horario_corregido = (d.get('horario_corregido') or '').strip() if resolucion != R.Resolucion.NO_ACREDITADA else ''
    r.horas_a_liquidar = horas
    r.observaciones = (d.get('observaciones') or '').strip()
    r.aprobado_por = d['aprobado_por'].strip()
    r.resuelta_por = request.user
    r.resuelta_el = timezone.now()
    r.estado = R.Estado.RESUELTA
    r.save()
    return Response(serializar(r))


@api_view(['POST'])
@permission_classes([EsAdmin])
def rectificacion_anular(request, rect_id):
    r = get_object_or_404(R, pk=rect_id)
    motivo = (request.data.get('motivo') or '').strip()
    if not motivo:
        return Response({'error': 'Indicá el motivo de la anulación.'}, status=400)
    if r.estado == R.Estado.RESUELTA and _mes_cerrado(r.fecha.strftime('%Y-%m')):
        return Response({'error': 'El mes está cerrado.'}, status=409)
    r.estado = R.Estado.ANULADA
    r.motivo_anulacion = motivo
    r.anulada_por = request.user
    r.anulada_el = timezone.now()
    r.save()
    return Response(serializar(r))


# ── Configuración ────────────────────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([EsAdminOColab])
def config(request):
    cfg = models.ConfigHorario.actual()
    if request.method == 'POST':
        if getattr(getattr(request.user, 'perfil', None), 'rol', None) != 'admin':
            return Response({'error': 'Sólo un administrador puede cambiar la configuración.'}, status=403)
        try:
            limite = int(request.data.get('limite_incidencias_mes'))
            if limite < 1 or limite > 31:
                raise ValueError
        except (TypeError, ValueError):
            return Response({'error': 'El límite tiene que ser un número entre 1 y 31.'}, status=400)
        cfg.limite_incidencias_mes = limite
        cfg.save()
    return Response({'limite_incidencias_mes': cfg.limite_incidencias_mes})


# ── Reporte mensual por empleado (PDF) ───────────────────────────────────────

def datos_reporte(emp, mes):
    y, m = [int(x) for x in mes.split('-')]
    qs = models.MarcaFichada.objects.filter(mes=mes, empleado=emp).select_related('empleado')
    detalle = build_detalle(qs, _errores_manuales_set(mes))
    rects_mes = list(rects.rectificaciones_qs(mes, emp))
    rects.aplicar_a_detalle(detalle, rects_mes)
    detalle = [f for f in detalle if f['nombre_raw'] == emp.nombre]

    ajuste = _ajustes_dict(mes).get(emp.nombre, {'faltas': [], 'feriados': [], 'vacaciones': {}, 'observacion': ''})
    resumen = monthly_summary(detalle, emp.nombre, mes, emp, ajuste)

    filas = []
    for f in detalle:
        fecha = date.fromisoformat(f['fecha'])
        rect = next((r for r in rects_mes if r.fecha == fecha), None)
        sistema = f.get('a_liquidar_sistema', f['a_liquidar'])
        filas.append({
            'fecha': fecha,
            'dia': DIAS[fecha.weekday()],
            'marcas': [(f.get(k) or '')[:5] for k in ('h1', 'h2', 'h3', 'h4')],
            'horas': f['horas'],
            'estado': f.get('estado_sistema') or f['estado'],
            'a_liquidar_sistema': sistema,
            'rect': rect,
            'a_liquidar': f['a_liquidar'],
            'corregido': rect is not None and rect.autoriza_correccion,
        })

    liquidaciones = models.LiquidacionHoras.objects.filter(empleado=emp, fecha__year=y, fecha__month=m).order_by('fecha')
    todas = list(models.RectificacionFichada.objects.filter(empleado=emp, fecha__year=y, fecha__month=m).order_by('fecha', 'id'))
    historial = models.HistorialMes.objects.filter(mes=mes).first()
    limite = models.ConfigHorario.actual().limite_incidencias_mes
    incidencias = len(rects_mes)
    dias_js = {1: 'lunes', 2: 'martes', 3: 'miércoles', 4: 'jueves', 5: 'viernes', 6: 'sábado', 0: 'domingo'}
    vacaciones = ajuste.get('vacaciones') or {}
    return {
        'datos_emp': datos_legajo(emp),
        'faltas_label': ', '.join(dias_js.get(int(x), str(x)) for x in ajuste.get('faltas') or []),
        'feriados_label': ', '.join(dias_js.get(int(x), str(x)) for x in ajuste.get('feriados') or []),
        'vacaciones_label': ', '.join(f'{v} {dias_js.get(int(k), k)}' for k, v in vacaciones.items() if int(v or 0)),
        'emp': emp,
        'mes': mes,
        'mes_label': f'{MESES[m - 1].capitalize()} {y}',
        'filas': filas,
        'resumen': resumen,
        'ajuste': ajuste,
        'rectificaciones': todas,
        'liquidaciones': liquidaciones,
        'total_liquidado': sum(float(l.monto) for l in liquidaciones),
        'incidencias': incidencias,
        'limite': limite,
        'supera_limite': incidencias >= limite,
        'dias_sin_descanso': sum(1 for f in filas if 'sin descanso' in f['estado'].lower() or 'descontó' in f['estado']),
        # Días sin marcas de descanso en los que se descontaron los 30 min (Reglamento §5).
        # Los días con una corrección autorizada quedan afuera: su cálculo lo definió la rectificación.
        'fechas_sin_descanso': [
            f['fecha'] for f in filas
            if ('sin descanso' in f['estado'].lower() or 'descontó' in f['estado']) and not f['corregido']
        ],
        'dias_error': sum(1 for f in filas if 'Error' in f['estado']),
        'cerrado': historial,
    }


@api_view(['GET'])
@permission_classes([EsAdminOColab])
def reporte_mensual(request):
    emp = get_object_or_404(models.Empleado, nombre=request.GET.get('empleado'))
    mes = request.GET.get('mes') or ''
    try:
        y, m = [int(x) for x in mes.split('-')]
        date(y, m, 1)
    except (ValueError, TypeError):
        return Response({'error': 'Mes inválido (YYYY-MM).'}, status=400)
    datos = datos_reporte(emp, mes)
    resp = _pdf('control_horario/reporte_mensual_pdf.html', datos,
                f'Reporte_horario_{mes}_{emp.nombre.replace(" ", "_")}.pdf')
    # Se descarga como archivo (para entregárselo al empleado)
    resp['Content-Disposition'] = resp['Content-Disposition'].replace('inline', 'attachment')
    return resp
