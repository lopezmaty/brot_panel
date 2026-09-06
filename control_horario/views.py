from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from users.permissions import EsAdmin
from . import models
from datetime import date, datetime, timezone as dt_tz
import calendar


# ============================================================
# CONSTANTES DE CÁLCULO (idénticas al HTML original)
# ============================================================
HORAS_ERROR_COMPLETA = 8.34
HORAS_ERROR_MEDIA = 4.2
DESCANSO_COMPLETA = 0.5    # 30 min
DESCANSO_MEDIA = 0.25      # 15 min

# Horario esperado por día de semana (JS weekday: 0=dom, 1=lun..6=sab)
SCHED_COMPLETA = {0: 0, 1: 9, 2: 8, 3: 8, 4: 8, 5: 9, 6: 0}
SCHED_MEDIA    = {0: 0, 1: 4.5, 2: 4, 3: 4, 4: 4, 5: 4.5, 6: 0}


# ============================================================
# LÓGICA DE CÁLCULO — PORT EXACTO DEL HTML ORIGINAL
# ============================================================

def mod_hours(a, b):
    """Horas entre dos momentos del mismo día, en decimal."""
    diff = b - a
    if diff < 0:
        diff += 24
    return diff


def compute_daily(marcas_del_dia, medio, sin_descanso):
    """Calcula horas de un día a partir de 2 o 4 marcas.
    Idéntico a computeDaily() del HTML original."""
    m = marcas_del_dia[:4]
    t = [d.hour + d.minute / 60 + d.second / 3600 for d in m]
    descanso = 0 if sin_descanso else (DESCANSO_MEDIA if medio else DESCANSO_COMPLETA)
    horas_error = HORAS_ERROR_MEDIA if medio else HORAS_ERROR_COMPLETA

    if len(m) == 2:
        bruto = mod_hours(t[0], t[1])
        horas = bruto
        a_liquidar = bruto - descanso
        if descanso > 0:
            estado = f'Calculado sin descanso marcado, se descontó {round(descanso, 2)} h'
        else:
            estado = 'Calculado sin descanso marcado (sin descuento de descanso)'
    elif len(m) == 4:
        horas = mod_hours(t[0], t[1]) + mod_hours(t[2], t[3])
        a_liquidar = horas
        estado = 'OK con descanso marcado'
    else:
        horas = None
        a_liquidar = horas_error
        estado = f'Error de fichada, cargar {round(horas_error, 2)} hs'

    return {'horas': horas, 'estado': estado, 'a_liquidar': a_liquidar}


def group_by_empleado_dia(marcas_qs):
    """Agrupa marcas por empleado+día. Devuelve lista de dicts."""
    grupos = {}
    for marca in marcas_qs.order_by('timestamp'):
        emp_id = marca.empleado_id
        dia = marca.timestamp.astimezone(dt_tz.utc).date()
        key = (emp_id, dia)
        if key not in grupos:
            grupos[key] = {'empleado': marca.empleado, 'fecha': dia, 'marcas': []}
        grupos[key]['marcas'].append(marca.timestamp.astimezone(dt_tz.utc))
    return list(grupos.values())


def build_detalle(marcas_qs, errores_manuales_set):
    """Construye el detalle diario. errores_manuales_set = set de (empleado_id, fecha)."""
    grupos = group_by_empleado_dia(marcas_qs)
    resultado = []
    for g in grupos:
        emp = g['empleado']
        medio = emp.medio_jornada
        sin_descanso = emp.sin_descuento_descanso
        c = compute_daily(g['marcas'], medio, sin_descanso)

        forzado = (emp.id, g['fecha']) in errores_manuales_set
        if forzado:
            horas_error = HORAS_ERROR_MEDIA if medio else HORAS_ERROR_COMPLETA
            resultado.append({
                'nombre': emp.nombre_display(),
                'nombre_raw': emp.nombre,
                'fecha': g['fecha'].isoformat(),
                'mes': g['fecha'].strftime('%Y-%m'),
                'h1': g['marcas'][0].strftime('%H:%M:%S') if len(g['marcas']) > 0 else None,
                'h2': g['marcas'][1].strftime('%H:%M:%S') if len(g['marcas']) > 1 else None,
                'h3': g['marcas'][2].strftime('%H:%M:%S') if len(g['marcas']) > 2 else None,
                'h4': g['marcas'][3].strftime('%H:%M:%S') if len(g['marcas']) > 3 else None,
                'horas': None,
                'a_liquidar': horas_error,
                'estado': f'Error de fichada, cargar {round(horas_error, 2)} hs (marcado manualmente)',
                'forzado': True,
            })
        else:
            resultado.append({
                'nombre': emp.nombre_display(),
                'nombre_raw': emp.nombre,
                'fecha': g['fecha'].isoformat(),
                'mes': g['fecha'].strftime('%Y-%m'),
                'h1': g['marcas'][0].strftime('%H:%M:%S') if len(g['marcas']) > 0 else None,
                'h2': g['marcas'][1].strftime('%H:%M:%S') if len(g['marcas']) > 1 else None,
                'h3': g['marcas'][2].strftime('%H:%M:%S') if len(g['marcas']) > 2 else None,
                'h4': g['marcas'][3].strftime('%H:%M:%S') if len(g['marcas']) > 3 else None,
                'horas': round(c['horas'], 4) if c['horas'] is not None else None,
                'a_liquidar': round(c['a_liquidar'], 4),
                'estado': c['estado'],
                'forzado': False,
            })
    return resultado


def horas_del_dia_semana(weekday_js, medio):
    """weekday_js: 0=dom, 1=lun ... 6=sab (mismo que JS)."""
    return (SCHED_MEDIA if medio else SCHED_COMPLETA).get(weekday_js, 0)


def horas_por_dias_seleccionados(dias, medio):
    """dias: lista de weekday_js. Suma horas esperadas para esos días."""
    return sum(horas_del_dia_semana(d, medio) for d in (dias or []))


def horas_por_conteo_dias(conteo, medio):
    """conteo: {str(weekday_js): int_cantidad}. Para vacaciones (varios lunes, martes, etc.)."""
    if not conteo:
        return 0
    total = 0
    for wd_str, cantidad in conteo.items():
        total += horas_del_dia_semana(int(wd_str), medio) * int(cantidad)
    return total


def expected_hours(year, month, medio):
    """Calcula horas esperadas del mes según el horario de Brot Panes."""
    total = 0
    for day in range(1, calendar.monthrange(year, month)[1] + 1):
        weekday_py = date(year, month, day).weekday()  # 0=lun..6=dom
        # convertir a JS style: 0=dom, 1=lun..6=sab
        weekday_js = (weekday_py + 1) % 7
        total += horas_del_dia_semana(weekday_js, medio)
    return total


def monthly_summary(detalle_rows, nombre_raw, mes_key, empleado_obj, ajuste):
    """Calcula el resumen mensual de un empleado. Port de monthlySummary() del HTML."""
    year, month = [int(x) for x in mes_key.split('-')]
    dias = [r for r in detalle_rows if r['nombre_raw'] == nombre_raw and r['mes'] == mes_key]

    medio = empleado_obj.medio_jornada
    bono_extra = float(empleado_obj.bono_horas_extra)

    credito_faltas = horas_por_dias_seleccionados(ajuste.get('faltas', []), medio)
    debito_feriados = horas_por_dias_seleccionados(ajuste.get('feriados', []), medio)
    debito_vacaciones = horas_por_conteo_dias(ajuste.get('vacaciones', {}), medio)

    total_horas_mes = sum(r['a_liquidar'] for r in dias) + credito_faltas
    dias_trabajados = len([r for r in dias if r['a_liquidar'] > 0]) + len(ajuste.get('faltas', []))
    dias_con_error = len([r for r in dias if 'Error' in r['estado']])
    horas_esperadas = expected_hours(year, month, medio) - debito_feriados - debito_vacaciones

    diferencia = total_horas_mes - horas_esperadas
    bono_compensado = 0
    if bono_extra > 0 and diferencia > 0:
        bono_compensado = min(diferencia, bono_extra)
        diferencia -= bono_compensado

    if abs(diferencia) < 0.01:
        estado = 'OK'
    elif diferencia < 0:
        estado = 'Faltan horas'
    else:
        estado = 'Horas extra'

    return {
        'nombre': empleado_obj.nombre_display(),
        'nombre_raw': nombre_raw,
        'mes': mes_key,
        'total_horas_mes': round(total_horas_mes, 4),
        'dias_trabajados': dias_trabajados,
        'dias_con_error': dias_con_error,
        'horas_esperadas': round(horas_esperadas, 4),
        'diferencia': round(diferencia, 4),
        'bono_extra': bono_extra,
        'bono_compensado': round(bono_compensado, 4),
        'estado': estado,
        'medio': medio,
        'sin_descanso': empleado_obj.sin_descuento_descanso,
        'faltas': ajuste.get('faltas', []),
        'feriados': ajuste.get('feriados', []),
        'vacaciones': ajuste.get('vacaciones', {}),
        'observacion': ajuste.get('observacion', ''),
        'debito_vacaciones': round(debito_vacaciones, 4),
    }


def _errores_manuales_set(mes=None):
    """Devuelve set de (empleado_id, fecha) para errores manuales."""
    qs = models.ErrorFichadaManual.objects.all()
    if mes:
        year, month = [int(x) for x in mes.split('-')]
        from datetime import date
        first = date(year, month, 1)
        last = date(year, month, calendar.monthrange(year, month)[1])
        qs = qs.filter(fecha__gte=first, fecha__lte=last)
    return {(e.empleado_id, e.fecha) for e in qs}


def _mes_cerrado(mes):
    return models.HistorialMes.objects.filter(mes=mes).exists()


def _ajustes_dict(mes=None):
    """Devuelve dict {nombre_raw: {faltas, feriados, vacaciones, observacion}}."""
    qs = models.AjusteMes.objects.select_related('empleado').all()
    if mes:
        qs = qs.filter(mes=mes)
    result = {}
    for a in qs:
        result[a.empleado.nombre] = {
            'faltas': a.faltas or [],
            'feriados': a.feriados or [],
            'vacaciones': a.vacaciones or {},
            'observacion': a.observacion or '',
        }
    return result


# ============================================================
# VISTA DE PÁGINA
# ============================================================

@login_required(login_url='login')
def control_horario_view(request):
    rol = request.user.perfil.rol
    if rol not in ('admin', 'colab'):
        return redirect('dashboard')
    return render(request, 'control_horario.html', {'es_admin': rol == 'admin'})


# ============================================================
# API — EMPLEADOS
# ============================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ch_empleados(request):
    empleados = models.Empleado.objects.filter(activo=True)
    data = [
        {
            'id': e.id,
            'nombre': e.nombre,
            'nombre_display': e.nombre_display(),
            'alias': e.alias,
            'medio_jornada': e.medio_jornada,
            'sin_descuento_descanso': e.sin_descuento_descanso,
            'bono_horas_extra': float(e.bono_horas_extra),
        }
        for e in empleados
    ]
    return Response(data)


@api_view(['POST'])
@permission_classes([EsAdmin])
def ch_empleados_update(request):
    """Actualiza configuración de empleados (solo admin)."""
    cambios = request.data.get('cambios', [])
    for c in cambios:
        try:
            emp = models.Empleado.objects.get(id=c['id'])
        except models.Empleado.DoesNotExist:
            continue
        if 'alias' in c:
            emp.alias = c['alias']
        if 'medio_jornada' in c:
            emp.medio_jornada = bool(c['medio_jornada'])
        if 'sin_descuento_descanso' in c:
            emp.sin_descuento_descanso = bool(c['sin_descuento_descanso'])
        if 'bono_horas_extra' in c:
            emp.bono_horas_extra = float(c['bono_horas_extra'])
        emp.save()
    return Response({'ok': True})


# ============================================================
# API — MESES DISPONIBLES / CERRADOS
# ============================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ch_meses(request):
    meses_marcas = list(
        models.MarcaFichada.objects.values_list('mes', flat=True).distinct().order_by('mes')
    )
    meses_historial = list(
        models.HistorialMes.objects.values_list('mes', flat=True).order_by('mes')
    )
    todos = sorted(set(meses_marcas + meses_historial))
    cerrados = set(meses_historial)
    return Response([
        {'mes': m, 'cerrado': m in cerrados}
        for m in todos
    ])


# ============================================================
# API — IMPORTAR FICHADAS
# ============================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ch_importar(request):
    """Importa fichadas de un mes desde el archivo del reloj biométrico.
    Acepta el mismo formato que el HTML: CSV/TSV con columna FechaHora."""
    mes = request.data.get('mes')
    texto = request.data.get('texto', '')
    ajustes_por_empleado = request.data.get('ajustes', {})

    if not mes:
        return Response({'error': 'Falta el mes.'}, status=400)
    if _mes_cerrado(mes):
        return Response({'error': f'El mes {mes} está cerrado y no se puede reimportar.'}, status=409)

    # Parsear el texto del reloj (mismo formato que el HTML)
    lineas_raw = _parse_fichadas(texto, mes)
    if not lineas_raw:
        return Response({'error': 'No se encontraron registros válidos en el archivo.'}, status=400)

    # Importar marcas
    nuevas = 0
    duplicadas = 0
    empleados_vistos = set()

    for nombre_raw, ts in lineas_raw:
        nombre_norm = _normalizar_nombre(nombre_raw)
        emp, _ = models.Empleado.objects.get_or_create(nombre=nombre_norm)
        empleados_vistos.add(nombre_norm)
        _, created = models.MarcaFichada.objects.get_or_create(
            empleado=emp,
            timestamp=ts,
            defaults={'mes': mes},
        )
        if created:
            nuevas += 1
        else:
            duplicadas += 1

    # Guardar ajustes por empleado
    for nombre, ajuste in ajustes_por_empleado.items():
        try:
            emp = models.Empleado.objects.get(nombre=nombre)
        except models.Empleado.DoesNotExist:
            continue
        models.AjusteMes.objects.update_or_create(
            empleado=emp,
            mes=mes,
            defaults={
                'faltas': ajuste.get('faltas', []),
                'feriados': ajuste.get('feriados', []),
                'vacaciones': ajuste.get('vacaciones', {}),
                'observacion': ajuste.get('observacion', ''),
            }
        )

    return Response({
        'ok': True,
        'nuevas': nuevas,
        'duplicadas': duplicadas,
        'empleados': sorted(empleados_vistos),
    })


def _normalizar_nombre(nombre):
    """Capitaliza cada palabra y strip, como normalizeName() del HTML."""
    return ' '.join(w.capitalize() for w in nombre.strip().split())


def _parse_fichadas(texto, mes_esperado):
    """Parsea el formato del reloj biométrico UDISKLOG (TAB-delimitado).
    Columnas UDISKLOG: No, Mchn, EnNo, Name, Mode, IOMd, DateTime
    También acepta CSV con ; o , y el formato anterior del HTML.
    Devuelve lista de (nombre, datetime UTC)."""
    resultado = []
    lineas = [l.rstrip('\r') for l in texto.replace('\r\n', '\n').split('\n')]
    lineas = [l for l in lineas if l.strip()]
    if not lineas:
        return resultado

    # Detectar delimitador desde las primeras líneas de datos
    delimitador = '\t'  # default para UDISKLOG
    for l in lineas:
        stripped = l.strip()
        if stripped and not stripped.startswith('UDISKLOG') and not stripped.startswith('No\t'):
            if ';' in stripped and '\t' not in stripped:
                delimitador = ';'
            elif ',' in stripped and '\t' not in stripped:
                delimitador = ','
            break

    # Índices por defecto para UDISKLOG: No(0) Mchn(1) EnNo(2) Name(3) Mode(4) IOMd(5) DateTime(6)
    col_nombre = 3
    col_fecha = 6

    for linea in lineas:
        parts = [p.strip() for p in linea.split(delimitador)]
        if len(parts) < 2:
            continue

        primera = parts[0].lower().strip()

        # Saltar líneas de cabecera/metadata
        if 'udisklog' in primera or primera in ('no', '#', ''):
            # UDISKLOG: el header tiene columnas vacías intercaladas que no aparecen
            # en las filas de datos. Solo actualizamos índices si el header NO tiene
            # columnas vacías (formato CSV estándar sin huecos).
            header_low = [p.strip().lower() for p in parts]
            non_empty = [h for h in header_low if h]
            if '' not in header_low:
                # CSV sin huecos: detectar índices normalmente
                for i, h in enumerate(header_low):
                    if h in ('nombre', 'name'):
                        col_nombre = i
                    if h in ('datetime', 'fechahora', 'fecha') or ('date' in h and 'time' in h):
                        col_fecha = i
            # Si hay huecos (UDISKLOG), dejamos los defaults 3 y 6 que son correctos
            continue

        # Saltar líneas que no son registros numéricos
        if not primera.replace('0', '').isdigit() and not primera.isdigit():
            continue

        if len(parts) <= max(col_nombre, col_fecha):
            continue

        nombre = parts[col_nombre].strip()
        fecha_str = parts[col_fecha].strip()

        if not nombre or not fecha_str:
            continue

        # Intentar múltiples formatos de fecha
        # Normalizar espacios múltiples (UDISKLOG usa doble espacio entre fecha y hora)
        fecha_norm = ' '.join(fecha_str.split())
        ts = None
        for fmt in (
            '%Y/%m/%d %H:%M:%S',   # UDISKLOG: 2026/08/03 05:42:54
            '%Y-%m-%d %H:%M:%S',   # estándar
            '%d/%m/%Y %H:%M:%S',   # dd/mm/yyyy
        ):
            try:
                ts = datetime.strptime(fecha_norm, fmt)
                break
            except ValueError:
                continue

        if ts is None:
            continue

        ts_utc = ts.replace(tzinfo=dt_tz.utc)
        mes_marca = ts_utc.strftime('%Y-%m')
        if mes_marca == mes_esperado:
            resultado.append((nombre, ts_utc))

    return resultado


# ============================================================
# API — PREVISUALIZAR EMPLEADOS DEL ARCHIVO (antes de importar)
# ============================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ch_preview_empleados(request):
    """Parsea el archivo y devuelve los empleados que trae, con sus ajustes
    ya guardados (si existen), para que el usuario configure antes de importar."""
    mes = request.data.get('mes')
    texto = request.data.get('texto', '')

    if not mes:
        return Response({'error': 'Falta el mes.'}, status=400)
    if _mes_cerrado(mes):
        return Response({'error': f'El mes {mes} está cerrado.'}, status=409)

    lineas = _parse_fichadas(texto, mes)
    nombres = sorted(set(_normalizar_nombre(n) for n, _ in lineas))

    ajustes_existentes = {}
    for nombre in nombres:
        try:
            emp = models.Empleado.objects.get(nombre=nombre)
            try:
                a = models.AjusteMes.objects.get(empleado=emp, mes=mes)
                ajustes_existentes[nombre] = {
                    'faltas': a.faltas,
                    'feriados': a.feriados,
                    'vacaciones': a.vacaciones,
                    'observacion': a.observacion,
                }
            except models.AjusteMes.DoesNotExist:
                ajustes_existentes[nombre] = {'faltas': [], 'feriados': [], 'vacaciones': {}, 'observacion': ''}
        except models.Empleado.DoesNotExist:
            ajustes_existentes[nombre] = {'faltas': [], 'feriados': [], 'vacaciones': {}, 'observacion': ''}

    return Response({
        'empleados': nombres,
        'total_marcas': len(lineas),
        'ajustes': ajustes_existentes,
    })


# ============================================================
# API — DETALLE DIARIO
# ============================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ch_detalle(request):
    mes = request.GET.get('mes')
    empleado = request.GET.get('empleado')

    qs = models.MarcaFichada.objects.select_related('empleado').all()
    if mes:
        qs = qs.filter(mes=mes)
    if empleado:
        qs = qs.filter(empleado__nombre=empleado)

    errores = _errores_manuales_set(mes)
    detalle = build_detalle(qs, errores)

    if empleado:
        detalle = [r for r in detalle if r['nombre_raw'] == empleado]

    return Response(detalle)


# ============================================================
# API — RESUMEN MENSUAL
# ============================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ch_resumen(request):
    mes = request.GET.get('mes')
    if not mes:
        return Response({'error': 'Falta el mes.'}, status=400)

    # Si el mes está cerrado, devolver el snapshot
    try:
        historial = models.HistorialMes.objects.get(mes=mes)
        return Response({
            'mes': mes,
            'cerrado': True,
            'cerrado_el': historial.cerrado_el.isoformat(),
            'snapshot': historial.snapshot,
        })
    except models.HistorialMes.DoesNotExist:
        pass

    qs = models.MarcaFichada.objects.filter(mes=mes).select_related('empleado')
    errores = _errores_manuales_set(mes)
    detalle = build_detalle(qs, errores)

    empleados = models.Empleado.objects.filter(activo=True)
    nombres_con_datos = {r['nombre_raw'] for r in detalle}
    empleados_mes = [e for e in empleados if e.nombre in nombres_con_datos]

    ajustes_qs = models.AjusteMes.objects.filter(mes=mes).select_related('empleado')
    ajustes_map = {a.empleado.nombre: {'faltas': a.faltas, 'feriados': a.feriados, 'vacaciones': a.vacaciones, 'observacion': a.observacion} for a in ajustes_qs}

    resumenes = []
    for emp in sorted(empleados_mes, key=lambda e: e.nombre):
        ajuste = ajustes_map.get(emp.nombre, {'faltas': [], 'feriados': [], 'vacaciones': {}, 'observacion': ''})
        r = monthly_summary(detalle, emp.nombre, mes, emp, ajuste)
        resumenes.append(r)

    # Advertencias: empleados con muchos menos días que el resto
    _agregar_advertencias(resumenes, detalle, mes)

    total_general = sum(r['total_horas_mes'] for r in resumenes)

    # Liquidaciones del mes (para evolución)
    liq_map = {}
    for liq in models.LiquidacionHoras.objects.filter(empleado__in=empleados_mes).select_related('empleado'):
        liq_map.setdefault(liq.empleado.nombre, []).append({
            'fecha': liq.fecha.isoformat(),
            'monto': float(liq.monto),
            'comentario': liq.comentario,
        })

    return Response({
        'mes': mes,
        'cerrado': False,
        'total_general': round(total_general, 2),
        'resumenes': resumenes,
        'liquidaciones': liq_map,
    })


def _agregar_advertencias(resumenes, detalle, mes):
    """Detecta empleados con menos días trabajados que el equipo (mismo patrón que el HTML)."""
    if not resumenes:
        return
    dias_por_emp = {r['nombre_raw']: set(row['fecha'] for row in detalle if row['nombre_raw'] == r['nombre_raw'] and row['mes'] == mes) for r in resumenes}
    todos_los_dias = set()
    for dias in dias_por_emp.values():
        todos_los_dias |= dias

    umbral = len(todos_los_dias) * 0.6
    for r in resumenes:
        dias_emp = dias_por_emp.get(r['nombre_raw'], set())
        dias_faltantes = sorted(todos_los_dias - dias_emp)
        if len(dias_faltantes) > len(todos_los_dias) * 0.4:
            r['advertencia'] = dias_faltantes
        else:
            r['advertencia'] = []


# ============================================================
# API — CERRAR / ABRIR MES
# ============================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ch_cerrar_mes(request):
    mes = request.data.get('mes')
    if not mes:
        return Response({'error': 'Falta el mes.'}, status=400)
    if _mes_cerrado(mes):
        return Response({'error': 'El mes ya está cerrado.'}, status=409)

    # Calcular y guardar snapshot
    qs = models.MarcaFichada.objects.filter(mes=mes).select_related('empleado')
    errores = _errores_manuales_set(mes)
    detalle = build_detalle(qs, errores)

    empleados = models.Empleado.objects.filter(activo=True)
    nombres_con_datos = {r['nombre_raw'] for r in detalle}
    empleados_mes = [e for e in empleados if e.nombre in nombres_con_datos]

    ajustes_qs = models.AjusteMes.objects.filter(mes=mes).select_related('empleado')
    ajustes_map = {a.empleado.nombre: {'faltas': a.faltas, 'feriados': a.feriados, 'vacaciones': a.vacaciones, 'observacion': a.observacion} for a in ajustes_qs}

    snapshot = {}
    for emp in empleados_mes:
        ajuste = ajustes_map.get(emp.nombre, {'faltas': [], 'feriados': [], 'vacaciones': {}, 'observacion': ''})
        r = monthly_summary(detalle, emp.nombre, mes, emp, ajuste)
        snapshot[emp.nombre] = {
            'total': r['total_horas_mes'],
            'esperadas': r['horas_esperadas'],
            'diferencia': r['diferencia'],
        }

    models.HistorialMes.objects.create(
        mes=mes,
        cerrado_por=request.user.username,
        snapshot=snapshot,
    )
    return Response({'ok': True, 'mes': mes})


@api_view(['POST'])
@permission_classes([EsAdmin])
def ch_abrir_mes(request):
    mes = request.data.get('mes')
    if not mes:
        return Response({'error': 'Falta el mes.'}, status=400)
    deleted, _ = models.HistorialMes.objects.filter(mes=mes).delete()
    if deleted == 0:
        return Response({'error': 'El mes no estaba cerrado.'}, status=404)
    return Response({'ok': True, 'mes': mes})


# ============================================================
# API — EVOLUCIÓN
# ============================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ch_evolucion(request):
    empleado_filtro = request.GET.get('empleado')

    # Todos los meses con datos
    meses_marcas = list(models.MarcaFichada.objects.values_list('mes', flat=True).distinct())
    meses_historial = list(models.HistorialMes.objects.values_list('mes', flat=True))
    todos_meses = sorted(set(meses_marcas + meses_historial))

    empleados = list(models.Empleado.objects.filter(activo=True))
    if empleado_filtro:
        empleados = [e for e in empleados if e.nombre == empleado_filtro]

    errores = _errores_manuales_set()
    detalle_all = build_detalle(
        models.MarcaFichada.objects.select_related('empleado').all(),
        errores,
    )

    ajustes_all = {(a.empleado.nombre, a.mes): {'faltas': a.faltas, 'feriados': a.feriados, 'vacaciones': a.vacaciones, 'observacion': a.observacion}
                   for a in models.AjusteMes.objects.select_related('empleado').all()}

    historial_map = {h.mes: h.snapshot for h in models.HistorialMes.objects.all()}

    liq_map = {}
    for liq in models.LiquidacionHoras.objects.select_related('empleado').all():
        liq_map.setdefault(liq.empleado.nombre, []).append({
            'fecha': liq.fecha.isoformat(),
            'monto': float(liq.monto),
            'comentario': liq.comentario,
            'registrado_el': liq.registrado_el.isoformat(),
        })

    datos = {}
    for mes in todos_meses:
        datos[mes] = {}
        for emp in empleados:
            if mes in historial_map and emp.nombre in historial_map[mes]:
                snap = historial_map[mes][emp.nombre]
                datos[mes][emp.nombre] = {
                    'diferencia': snap.get('diferencia', snap.get('diferencia', 0)),
                    'cerrado': True,
                }
            else:
                ajuste = ajustes_all.get((emp.nombre, mes), {'faltas': [], 'feriados': [], 'vacaciones': {}, 'observacion': ''})
                r = monthly_summary(detalle_all, emp.nombre, mes, emp, ajuste)
                if any(row['nombre_raw'] == emp.nombre and row['mes'] == mes for row in detalle_all):
                    datos[mes][emp.nombre] = {
                        'diferencia': r['diferencia'],
                        'cerrado': False,
                    }

    return Response({
        'meses': todos_meses,
        'empleados': [{'nombre': e.nombre, 'nombre_display': e.nombre_display()} for e in empleados],
        'datos': datos,
        'liquidaciones': liq_map,
    })


# ============================================================
# API — LIQUIDACIONES
# ============================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ch_liquidar(request):
    nombre = request.data.get('empleado')
    fecha = request.data.get('fecha')
    monto = request.data.get('monto')
    comentario = request.data.get('comentario', '')

    if not all([nombre, fecha, monto]):
        return Response({'error': 'Faltan datos.'}, status=400)

    try:
        emp = models.Empleado.objects.get(nombre=nombre)
    except models.Empleado.DoesNotExist:
        return Response({'error': 'Empleado no encontrado.'}, status=404)

    from datetime import date as date_cls
    liq = models.LiquidacionHoras.objects.create(
        empleado=emp,
        fecha=date_cls.fromisoformat(fecha),
        monto=float(monto),
        comentario=comentario,
    )
    return Response({'ok': True, 'id': liq.id})


@api_view(['DELETE'])
@permission_classes([EsAdmin])
def ch_eliminar_liquidacion(request, liq_id):
    try:
        liq = models.LiquidacionHoras.objects.get(id=liq_id)
        liq.delete()
        return Response({'ok': True})
    except models.LiquidacionHoras.DoesNotExist:
        return Response({'error': 'No encontrada.'}, status=404)


# ============================================================
# API — AJUSTES (guardar feriados/faltas/vacaciones por empleado)
# ============================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ch_guardar_ajuste(request):
    nombre = request.data.get('empleado')
    mes = request.data.get('mes')
    if not nombre or not mes:
        return Response({'error': 'Faltan datos.'}, status=400)
    if _mes_cerrado(mes):
        return Response({'error': 'El mes está cerrado.'}, status=409)

    try:
        emp = models.Empleado.objects.get(nombre=nombre)
    except models.Empleado.DoesNotExist:
        return Response({'error': 'Empleado no encontrado.'}, status=404)

    models.AjusteMes.objects.update_or_create(
        empleado=emp,
        mes=mes,
        defaults={
            'faltas': request.data.get('faltas', []),
            'feriados': request.data.get('feriados', []),
            'vacaciones': request.data.get('vacaciones', {}),
            'observacion': request.data.get('observacion', ''),
        }
    )
    return Response({'ok': True})


# ============================================================
# API — DATOS RESUMEN (para sidebar)
# ============================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ch_data_summary(request):
    total_marcas = models.MarcaFichada.objects.count()
    total_empleados = models.Empleado.objects.filter(activo=True).count()
    meses = sorted(set(
        list(models.MarcaFichada.objects.values_list('mes', flat=True).distinct()) +
        list(models.HistorialMes.objects.values_list('mes', flat=True))
    ))
    return Response({
        'total_marcas': total_marcas,
        'total_empleados': total_empleados,
        'meses': meses,
    })