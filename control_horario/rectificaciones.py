"""Rectificaciones excepcionales de fichada (Reglamento de Registro Horario, §8 y Anexo I).

Las marcas del reloj nunca se modifican: la rectificación se guarda aparte y,
cuando se autoriza, sólo reemplaza las horas a liquidar de ese día.
"""
import calendar
from datetime import date, datetime, timedelta
from datetime import timezone as dt_tz

from django.utils import timezone

from . import models

R = models.RectificacionFichada

TIPOS_LABEL = dict(R.TIPOS)
# Por decisión de la empresa sólo se rectifican marcas de entrada y de salida
TIPOS_PERMITIDOS = ('ingreso', 'salida')
DESCANSO_COMPLETA = 0.5


def rectificaciones_qs(mes=None, empleado=None):
    qs = R.objects.select_related('empleado').exclude(estado=R.Estado.ANULADA)
    if mes:
        year, month = [int(x) for x in mes.split('-')]
        qs = qs.filter(fecha__gte=date(year, month, 1), fecha__lte=date(year, month, calendar.monthrange(year, month)[1]))
    if empleado:
        qs = qs.filter(empleado=empleado)
    return qs


def _mapa(rectificaciones):
    """{(empleado_id, fecha): rectificación}. Si hay más de una para el mismo día,
    manda la que autoriza la corrección y, si no, la más reciente."""
    mapa = {}
    for r in sorted(rectificaciones, key=lambda x: x.id):
        key = (r.empleado_id, r.fecha)
        actual = mapa.get(key)
        if actual is None or r.autoriza_correccion or not actual.autoriza_correccion:
            mapa[key] = r
    return mapa


def resumen_corto(r):
    return {
        'id': r.id,
        'numero': r.numero,
        'estado': r.estado,
        'estado_label': r.get_estado_display(),
        'resolucion': r.resolucion,
        'horas_a_liquidar': float(r.horas_a_liquidar) if r.horas_a_liquidar is not None else None,
        'horario_corregido': r.horario_corregido,
        'fuera_de_termino': r.aviso_fuera_de_termino,
    }


def aplicar_a_detalle(detalle, rectificaciones, empleados_por_id=None):
    """Aplica las rectificaciones al detalle diario (lista de filas de build_detalle).

    - Días con marcas: si la rectificación está autorizada, reemplaza "a_liquidar"
      y guarda el cálculo original del sistema en "a_liquidar_sistema".
    - Días sin ninguna marca: agrega una fila (con 0 h si todavía no se autorizó).
    """
    rects = list(rectificaciones)
    if not rects:
        for row in detalle:
            row.setdefault('rectificacion', None)
        return detalle

    mapa = _mapa(rects)
    nombres_a_id = {r.empleado.nombre: r.empleado_id for r in rects}
    if empleados_por_id:
        nombres_a_id.update({e.nombre: e.id for e in empleados_por_id.values()})

    vistos = set()
    for row in detalle:
        emp_id = nombres_a_id.get(row['nombre_raw'])
        fecha = date.fromisoformat(row['fecha'])
        rect = mapa.get((emp_id, fecha)) if emp_id else None
        row['rectificacion'] = resumen_corto(rect) if rect else None
        if rect:
            vistos.add((emp_id, fecha))
            if rect.autoriza_correccion:
                row['a_liquidar_sistema'] = row['a_liquidar']
                row['estado_sistema'] = row['estado']
                row['a_liquidar'] = float(rect.horas_a_liquidar)
                row['estado'] = f'Rectificación autorizada (N° {rect.numero})'

    for (emp_id, fecha), rect in mapa.items():
        if (emp_id, fecha) in vistos:
            continue
        autorizada = rect.autoriza_correccion
        detalle.append({
            'nombre': rect.empleado.nombre_display(),
            'nombre_raw': rect.empleado.nombre,
            'fecha': fecha.isoformat(),
            'mes': fecha.strftime('%Y-%m'),
            'h1': None, 'h2': None, 'h3': None, 'h4': None,
            'horas': None,
            'a_liquidar': float(rect.horas_a_liquidar) if autorizada else 0.0,
            'a_liquidar_sistema': 0.0,
            'estado': f'Rectificación autorizada (N° {rect.numero})' if autorizada else 'Sin marcas en el reloj',
            'estado_sistema': 'Sin marcas en el reloj',
            'forzado': False,
            'es_error_manual': False,
            'sin_marcas': True,
            'rectificacion': resumen_corto(rect),
        })
    detalle.sort(key=lambda r: (r['nombre_raw'], r['fecha']))
    return detalle


def incidencias_por_empleado(mes):
    """{nombre_raw: cantidad de rectificaciones (no anuladas) del mes}."""
    conteo = {}
    for r in rectificaciones_qs(mes):
        conteo[r.empleado.nombre] = conteo.get(r.empleado.nombre, 0) + 1
    return conteo


def horas_declaradas(entrada, salida_desc, regreso_desc, salida, empleado, sin_descanso_declarado=False):
    """Horas según el horario real que informa el trabajador (misma regla que el sistema)."""
    def h(t):
        return t.hour + t.minute / 60 if t else None

    e, sd, rd, s = h(entrada), h(salida_desc), h(regreso_desc), h(salida)
    if e is None or s is None:
        return None
    total = (s - e) % 24
    if sd is not None and rd is not None:
        total -= (rd - sd) % 24
    elif not sin_descanso_declarado and not empleado.sin_descuento_descanso and not empleado.medio_jornada:
        total -= DESCANSO_COMPLETA
    return round(max(total, 0), 2)


def formatear_marcas(fila):
    if not fila:
        return 'Sin marcas registradas en el reloj ese día.'
    etiquetas = ['Entrada', 'Salida descanso', 'Regreso descanso', 'Salida final']
    marcas = [fila.get(k) for k in ('h1', 'h2', 'h3', 'h4')]
    presentes = [m for m in marcas if m]
    if len(presentes) == 2:
        return f'Entrada {presentes[0][:5]}. Salida final {presentes[1][:5]}. Descanso: SIN MARCA.'
    partes = []
    for et, m in zip(etiquetas, marcas):
        partes.append(f'{et} {m[:5]}' if m else f'{et}: SIN MARCA')
    return '. '.join(partes) + '.'


def formatear_calculo(fila):
    if not fila:
        return 'Sin marcas: el sistema no liquida horas para ese día.'
    horas = fila.get('a_liquidar')
    return f"{fila.get('estado_sistema') or fila.get('estado')}. A liquidar según el sistema: {horas:.2f} h."


def ahora():
    return timezone.now()
