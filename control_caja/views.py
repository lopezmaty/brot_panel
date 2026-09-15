import json
from decimal import Decimal, InvalidOperation
from datetime import date

import pandas as pd

from django.http import JsonResponse
from django.shortcuts import render
from django.db.models import Sum

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from .models import (
    MovimientoCaja, CierreDiario, ConciliacionItem,
    SaldoInicial, TIPOS_INGRESO, TIPOS_EGRESO
)


def es_admin(user):
    return hasattr(user, 'perfil') and user.perfil.rol == 'admin'


def es_colab(user):
    return hasattr(user, 'perfil') and user.perfil.rol in ('admin', 'colab')


def _normalizar_nro(nro):
    """Normaliza 1-558 → 0001-00000558"""
    if not nro:
        return ''
    partes = nro.strip().split('-')
    if len(partes) == 2:
        try:
            return f'{int(partes[0]):04d}-{int(partes[1]):08d}'
        except ValueError:
            pass
    return nro.strip()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def control_caja_view_api(request):
    return JsonResponse({'ok': True})


from django.contrib.auth.decorators import login_required


@login_required
def control_caja_view(request):
    from django.shortcuts import render
    return render(request, 'control_caja.html', {
        'es_admin': es_admin(request.user),
    })


# ── SALDO INICIAL ──────────────────────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def api_saldo_inicial(request):
    obj, _ = SaldoInicial.objects.get_or_create(pk=1)
    if request.method == 'GET':
        return JsonResponse({'monto': float(obj.monto)})

    if not es_admin(request.user):
        return JsonResponse({'error': 'Solo admin'}, status=403)

    data = request.data
    try:
        obj.monto = Decimal(str(data['monto']))
        obj.actualizado_por = request.user
        obj.save()
        return JsonResponse({'ok': True, 'monto': float(obj.monto)})
    except (KeyError, InvalidOperation):
        return JsonResponse({'error': 'Monto inválido'}, status=400)


# ── MOVIMIENTOS ────────────────────────────────────────────────────────────────

def _calcular_estado(m):
    if m.campos_completos():
        return 'bloqueado'
    return 'parcial'


def _movimiento_a_dict(m):
    return {
        'id': m.id,
        'fecha': m.fecha.isoformat() if m.fecha and hasattr(m.fecha, 'isoformat') else str(m.fecha) if m.fecha else None,
        'tipo': m.tipo,
        'cliente_proveedor': m.cliente_proveedor,
        'detalle': m.detalle,
        'nro_comprobante': m.nro_comprobante,
        'nro_recibo_op': m.nro_recibo_op,
        'monto': float(m.monto) if m.monto is not None else None,
        'conciliado': m.conciliado,
        'observaciones': m.observaciones,
        'estado': m.estado,
        'es_ingreso': m.es_ingreso(),
    }


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def api_movimientos(request):
    if request.method == 'GET':
        fecha_desde = request.GET.get('fecha_desde')
        fecha_hasta = request.GET.get('fecha_hasta')
        qs = MovimientoCaja.objects.all()
        if fecha_desde:
            qs = qs.filter(fecha__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(fecha__lte=fecha_hasta)
        return JsonResponse({'movimientos': [_movimiento_a_dict(m) for m in qs]})

    if not es_colab(request.user):
        return JsonResponse({'error': 'Sin permiso'}, status=403)

    data = request.data
    m = MovimientoCaja(creado_por=request.user)
    m.fecha = data.get('fecha') or None
    m.tipo = data.get('tipo', '')
    m.cliente_proveedor = data.get('cliente_proveedor', '')
    m.detalle = data.get('detalle', '')
    m.nro_comprobante = _normalizar_nro(data.get('nro_comprobante', ''))
    m.nro_recibo_op = _normalizar_nro(data.get('nro_recibo_op', ''))
    raw_monto = data.get('monto')
    m.monto = Decimal(str(raw_monto)) if raw_monto not in (None, '') else None
    m.observaciones = data.get('observaciones', '')
    m.estado = _calcular_estado(m)
    m.save()
    return JsonResponse(_movimiento_a_dict(m), status=201)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def api_movimiento_detalle(request, pk):
    try:
        m = MovimientoCaja.objects.get(pk=pk)
    except MovimientoCaja.DoesNotExist:
        return JsonResponse({'error': 'No existe'}, status=404)

    if request.method == 'GET':
        return JsonResponse(_movimiento_a_dict(m))

    if m.estado == 'bloqueado' and not es_admin(request.user):
        return JsonResponse({'error': 'Movimiento bloqueado'}, status=403)

    if not es_colab(request.user):
        return JsonResponse({'error': 'Sin permiso'}, status=403)

    if request.method == 'DELETE':
        if not es_admin(request.user):
            return JsonResponse({'error': 'Solo admin puede eliminar'}, status=403)
        m.delete()
        return JsonResponse({'ok': True})

    data = request.data

    # Admin puede desbloquear manualmente
    if es_admin(request.user) and 'estado' in data and len(data) == 1:
        nuevo_estado = data['estado']
        if nuevo_estado in ('bloqueado', 'parcial'):
            m.estado = nuevo_estado
            m.save()
            return JsonResponse(_movimiento_a_dict(m))

    m.fecha = data.get('fecha') or None
    m.tipo = data.get('tipo', m.tipo)
    m.cliente_proveedor = data.get('cliente_proveedor', m.cliente_proveedor)
    m.detalle = data.get('detalle', m.detalle)
    m.nro_comprobante = _normalizar_nro(data.get('nro_comprobante', m.nro_comprobante))
    m.nro_recibo_op = _normalizar_nro(data.get('nro_recibo_op', m.nro_recibo_op))
    raw_monto = data.get('monto')
    if raw_monto not in (None, ''):
        m.monto = Decimal(str(raw_monto))
    m.observaciones = data.get('observaciones', m.observaciones)
    m.estado = _calcular_estado(m)
    m.save()
    return JsonResponse(_movimiento_a_dict(m))


# ── CIERRE DIARIO ──────────────────────────────────────────────────────────────

def _saldo_teorico_dia(fecha):
    saldo_inicial = float(SaldoInicial.objects.get_or_create(pk=1)[0].monto)
    movimientos = MovimientoCaja.objects.filter(
        fecha__lte=fecha,
        estado__in=('completo', 'bloqueado'),
    )
    total = saldo_inicial
    for m in movimientos:
        if m.monto is not None:
            if m.es_ingreso():
                total += float(m.monto)
            else:
                total -= float(m.monto)
    return round(total, 2)


def _cierre_a_dict(c):
    saldo_teorico = _saldo_teorico_dia(c.fecha)
    efectivo = float(c.efectivo_contado) if c.efectivo_contado is not None else None
    diferencia = round(efectivo - saldo_teorico, 2) if efectivo is not None else None
    return {
        'id': c.id,
        'fecha': c.fecha.isoformat(),
        'saldo_teorico': saldo_teorico,
        'efectivo_contado': efectivo,
        'diferencia': diferencia,
        'responsable': c.responsable,
        'observaciones': c.observaciones,
        'cierra_ok': diferencia == 0 if diferencia is not None else None,
    }


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def api_cierre_diario(request):
    if request.method == 'GET':
        fecha_desde = request.GET.get('fecha_desde')
        fecha_hasta = request.GET.get('fecha_hasta')
        qs = CierreDiario.objects.all()
        if fecha_desde:
            qs = qs.filter(fecha__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(fecha__lte=fecha_hasta)
        return JsonResponse({'cierres': [_cierre_a_dict(c) for c in qs]})

    if not es_colab(request.user):
        return JsonResponse({'error': 'Sin permiso'}, status=403)

    data = request.data
    fecha = data.get('fecha')
    if not fecha:
        return JsonResponse({'error': 'Fecha requerida'}, status=400)

    c, _ = CierreDiario.objects.get_or_create(fecha=fecha)
    raw = data.get('efectivo_contado')
    c.efectivo_contado = Decimal(str(raw)) if raw not in (None, '') else None
    c.responsable = data.get('responsable', c.responsable)
    c.observaciones = data.get('observaciones', c.observaciones)
    c.creado_por = request.user
    c.save()
    return JsonResponse(_cierre_a_dict(c), status=201)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def api_cierre_diario_detalle(request, pk):
    try:
        c = CierreDiario.objects.get(pk=pk)
    except CierreDiario.DoesNotExist:
        return JsonResponse({'error': 'No existe'}, status=404)

    if not es_colab(request.user):
        return JsonResponse({'error': 'Sin permiso'}, status=403)

    data = request.data
    raw = data.get('efectivo_contado')
    c.efectivo_contado = Decimal(str(raw)) if raw not in (None, '') else None
    c.responsable = data.get('responsable', c.responsable)
    c.observaciones = data.get('observaciones', c.observaciones)
    c.save()
    return JsonResponse(_cierre_a_dict(c))


# ── CONCILIACIÓN ───────────────────────────────────────────────────────────────

def _normalizar_nro_xubio(nro):
    """C-0001-00003178 → 0001-00003178"""
    if not nro:
        return ''
    partes = nro.strip().split('-')
    if len(partes) == 3 and partes[0] in ('C', 'X'):
        return f'{partes[1]}-{partes[2]}'
    return nro.strip()


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_conciliacion_importar(request):
    if not es_admin(request.user):
        return JsonResponse({'error': 'Solo admin'}, status=403)

    archivo = request.FILES.get('archivo')
    if not archivo:
        return JsonResponse({'error': 'No se envió archivo'}, status=400)

    try:
        df = pd.read_excel(archivo)
        df = df[df['Cuenta'].str.strip().str.lower() == 'caja']
        df = df[~df['Tipo'].str.strip().str.lower().str.contains('ajuste')]
    except Exception as e:
        return JsonResponse({'error': f'Error leyendo archivo: {str(e)}'}, status=400)

    ConciliacionItem.objects.all().delete()

    resultados = {'ok': 0, 'falta_en_caja': 0, 'monto_difiere': 0}

    for _, row in df.iterrows():
        try:
            nro_xubio = str(row.get('Comprobante', '')).strip()
            nro_normalizado = _normalizar_nro_xubio(nro_xubio)
            fecha_xubio = pd.to_datetime(row['Fecha']).date()
            importe_xubio = Decimal(str(row['Importe']))
            cliente_xubio = str(row.get('Cliente', '')).strip()

            movimiento = None
            if nro_normalizado:
                for c in MovimientoCaja.objects.filter(nro_recibo_op__endswith=nro_normalizado.split('-')[-1]):
                    if c.nro_recibo_normalizado() == nro_normalizado:
                        movimiento = c
                        break

            if movimiento is None:
                estado = 'falta_en_caja'
                diferencia = importe_xubio
            elif movimiento.monto is None:
                estado = 'monto_difiere'
                diferencia = importe_xubio
            else:
                diff = abs(float(importe_xubio) - float(movimiento.monto))
                if diff < 1:
                    estado = 'ok'
                    diferencia = Decimal(str(round(float(importe_xubio) - float(movimiento.monto), 2)))
                else:
                    estado = 'monto_difiere'
                    diferencia = Decimal(str(round(float(importe_xubio) - float(movimiento.monto), 2)))

            ConciliacionItem.objects.create(
                fecha_xubio=fecha_xubio,
                nro_comprobante_xubio=nro_xubio,
                cliente_xubio=cliente_xubio,
                importe_xubio=importe_xubio,
                movimiento_caja=movimiento,
                estado=estado,
                diferencia=diferencia,
            )

            if movimiento and estado == 'ok':
                movimiento.conciliado = True
                movimiento.save()

            resultados[estado] = resultados.get(estado, 0) + 1

        except Exception:
            continue

    return JsonResponse({'ok': True, 'resultados': resultados})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_conciliacion_listar(request):
    if not es_admin(request.user):
        return JsonResponse({'error': 'Solo admin'}, status=403)

    items = ConciliacionItem.objects.select_related('movimiento_caja').all()
    return JsonResponse({'items': [
        {
            'id': i.id,
            'fecha_xubio': i.fecha_xubio.isoformat(),
            'nro_comprobante_xubio': i.nro_comprobante_xubio,
            'cliente_xubio': i.cliente_xubio,
            'importe_xubio': float(i.importe_xubio),
            'estado': i.estado,
            'diferencia': float(i.diferencia),
            'movimiento_id': i.movimiento_caja_id,
            'nro_recibo_caja': i.movimiento_caja.nro_recibo_op if i.movimiento_caja else None,
            'monto_caja': float(i.movimiento_caja.monto) if i.movimiento_caja and i.movimiento_caja.monto else None,
        }
        for i in items
    ]})


# ── RESUMEN MENSUAL ────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_resumen_mensual(request):
    if not es_admin(request.user):
        return JsonResponse({'error': 'Solo admin'}, status=403)

    anio = int(request.GET.get('anio', date.today().year))
    meses = list(range(1, 13))
    tipos = [t[0] for t in MovimientoCaja._meta.get_field('tipo').choices]

    resultado = {}
    for tipo in tipos:
        resultado[tipo] = {}
        for mes in meses:
            agg = MovimientoCaja.objects.filter(
                tipo=tipo,
                fecha__year=anio,
                fecha__month=mes,
                estado__in=('completo', 'bloqueado'),
            ).aggregate(total=Sum('monto'))
            resultado[tipo][mes] = float(agg['total'] or 0)

    totales_ingresos = {}
    totales_egresos = {}
    for mes in meses:
        totales_ingresos[mes] = sum(resultado[t][mes] for t in tipos if t in TIPOS_INGRESO)
        totales_egresos[mes] = sum(resultado[t][mes] for t in tipos if t in TIPOS_EGRESO)

    return JsonResponse({
        'anio': anio,
        'tipos': resultado,
        'totales_ingresos': totales_ingresos,
        'totales_egresos': totales_egresos,
    })
