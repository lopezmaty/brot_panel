from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.db.models import Max, Q, Sum
from django.shortcuts import redirect, render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from users.permissions import EsAdmin

from . import models
from .importador_xubio import ErrorImportacion, aplicar, leer_excel, planificar
from .services_flujo import DIAS_MAX_VENCIDO_CLIENTES, calcular_flujo, ultimo_dia_del_mes


# ── Página ──────────────────────────────────────────────────────────────────
@login_required(login_url='login')
def flujo_fondos_view(request):
    if request.user.perfil.rol != 'admin':
        return redirect('dashboard')
    return render(request, 'flujo_fondos.html')


# ── Helpers ─────────────────────────────────────────────────────────────────
class DatoInvalido(Exception):
    pass


def _decimal(valor, positivo=True):
    try:
        d = Decimal(str(valor))
    except (InvalidOperation, ValueError):
        raise DatoInvalido('Importe inválido')
    if positivo and d <= 0:
        raise DatoInvalido('El importe debe ser mayor a cero')
    return d


def _fecha(valor, obligatoria=True):
    if not valor:
        if obligatoria:
            raise DatoInvalido('Falta una fecha')
        return None
    try:
        return date.fromisoformat(valor)
    except ValueError:
        raise DatoInvalido('Fecha inválida')


def _item_dict(i):
    return {
        'id': i.pk, 'tipo': i.tipo, 'contraparte': i.contraparte, 'comprobante': i.comprobante,
        'fecha_emision': i.fecha_emision.isoformat() if i.fecha_emision else None,
        'fecha_vencimiento': i.fecha_vencimiento.isoformat(),
        'importe': float(i.importe), 'estado': i.estado,
        'fecha_cancelacion': i.fecha_cancelacion.isoformat() if i.fecha_cancelacion else None,
        'observaciones': i.observaciones, 'origen': i.origen,
    }


def _saldo_dict(s):
    return {'id': s.pk, 'cuenta': s.cuenta, 'cuenta_label': s.get_cuenta_display(),
            'fecha': s.fecha.isoformat(), 'monto': float(s.monto)}


# ── Resumen ─────────────────────────────────────────────────────────────────
@api_view(['GET'])
@permission_classes([EsAdmin])
def ff_resumen(request):
    # La fecha de corte puede venir como fecha exacta (corte=YYYY-MM-DD, por ejemplo hoy)
    # o como mes (mes=YYYY-MM), que toma el último día de ese mes.
    try:
        if request.GET.get('corte'):
            corte = date.fromisoformat(request.GET['corte'])
        else:
            corte = ultimo_dia_del_mes(request.GET.get('mes', ''))
    except (ValueError, TypeError):
        return Response({'error': 'Fecha de corte inválida.'}, status=400)

    r = calcular_flujo(corte)
    for m in r['matriz']:
        for k, v in m.items():
            if isinstance(v, Decimal):
                m[k] = float(v)
    r['kpis'] = {k: float(v) for k, v in r['kpis'].items()}
    for s in r['semanas']:
        s['desde'], s['hasta'] = s['desde'].isoformat(), s['hasta'].isoformat()
        for k in ('cobros', 'pagos', 'neto', 'acumulada'):
            s[k] = float(s[k])
    r['corte'] = corte.isoformat()
    return Response(r)


# ── Cuentas corrientes ──────────────────────────────────────────────────────
def _aplicar_campos(item, data):
    tipo = data.get('tipo')
    if tipo not in ('cliente', 'proveedor'):
        raise DatoInvalido('Elegí cliente o proveedor')
    contraparte = (data.get('contraparte') or '').strip()
    if not contraparte:
        raise DatoInvalido('Falta el nombre del cliente o proveedor')
    comprobante = (data.get('comprobante') or '').strip()[:60]
    if comprobante and models.CuentaCorrienteItem.objects.filter(
        tipo=tipo, contraparte__iexact=contraparte, comprobante__iexact=comprobante
    ).exclude(pk=item.pk).exists():
        raise DatoInvalido('Ya cargaste ese comprobante para ese cliente/proveedor')
    item.tipo, item.contraparte, item.comprobante = tipo, contraparte[:150], comprobante
    item.fecha_emision = _fecha(data.get('fecha_emision'), obligatoria=False)
    item.fecha_vencimiento = _fecha(data.get('fecha_vencimiento'))
    item.importe = _decimal(data.get('importe'))
    item.observaciones = (data.get('observaciones') or '').strip()[:300]
    item.save()
    return item


@api_view(['GET', 'POST'])
@permission_classes([EsAdmin])
def ff_cuentas(request):
    if request.method == 'GET':
        p = request.GET
        qs = models.CuentaCorrienteItem.objects.all()
        if p.get('tipo'):
            qs = qs.filter(tipo=p['tipo'])
        if p.get('estado'):
            qs = qs.filter(estado=p['estado'])
        if p.get('q'):
            qs = qs.filter(Q(contraparte__icontains=p['q']) | Q(comprobante__icontains=p['q']))
        if p.get('desde'):
            qs = qs.filter(fecha_vencimiento__gte=p['desde'])
        if p.get('hasta'):
            qs = qs.filter(fecha_vencimiento__lte=p['hasta'])
        tot = {t['tipo']: float(t['s']) for t in
               qs.filter(estado='pendiente').order_by().values('tipo').annotate(s=Sum('importe'))}
        ultima = {
            t['tipo']: t['m'].isoformat()
            for t in models.CuentaCorrienteItem.objects.filter(origen='import')
            .order_by().values('tipo').annotate(m=Max('modificado_en'))
        }
        return Response({
            'cuentas': [_item_dict(i) for i in qs[:500]],
            'totales': {'cobrar': tot.get('cliente', 0), 'pagar': tot.get('proveedor', 0)},
            'ultima_importacion': {'cliente': ultima.get('cliente'), 'proveedor': ultima.get('proveedor')},
            'dias_max_vencido_clientes': DIAS_MAX_VENCIDO_CLIENTES,
        })
    try:
        item = _aplicar_campos(models.CuentaCorrienteItem(), request.data)
    except DatoInvalido as e:
        return Response({'error': str(e)}, status=400)
    return Response(_item_dict(item), status=201)


@api_view(['PUT', 'DELETE'])
@permission_classes([EsAdmin])
def ff_cuenta_detalle(request, pk):
    try:
        item = models.CuentaCorrienteItem.objects.get(pk=pk)
    except models.CuentaCorrienteItem.DoesNotExist:
        return Response({'error': 'No existe'}, status=404)
    if request.method == 'DELETE':
        item.delete()
        return Response({'ok': True})
    try:
        _aplicar_campos(item, request.data)
    except DatoInvalido as e:
        return Response({'error': str(e)}, status=400)
    return Response(_item_dict(item))


@api_view(['POST'])
@permission_classes([EsAdmin])
def ff_cuenta_saldar(request, pk):
    """Registrar cobro/pago. Si el monto es menor al importe, queda el resto pendiente."""
    try:
        item = models.CuentaCorrienteItem.objects.get(pk=pk, estado='pendiente')
    except models.CuentaCorrienteItem.DoesNotExist:
        return Response({'error': 'No existe o ya está cancelado'}, status=404)
    try:
        fecha = _fecha(request.data.get('fecha'))
        monto = _decimal(request.data.get('monto') or item.importe)
    except DatoInvalido as e:
        return Response({'error': str(e)}, status=400)
    if monto < item.importe:
        item.importe -= monto
    else:
        item.estado, item.fecha_cancelacion = 'cancelado', fecha
    item.save()
    return Response(_item_dict(item))


# ── Importar reportes de Xubio (Excel) ──────────────────────────────────────
TAMANIO_MAX_EXCEL = 5 * 1024 * 1024   # 5 MB


@api_view(['POST'])
@permission_classes([EsAdmin])
def ff_importar(request):
    """
    Recibe el Excel de "Cuentas a cobrar" o "Cuentas a pagar" de Xubio.
    confirmar=false (o ausente): solo devuelve el resumen de lo que pasaría.
    confirmar=true: aplica los cambios.
    """
    archivo = request.FILES.get('archivo')
    if archivo is None:
        return Response({'error': 'Elegí un archivo.'}, status=400)
    if not archivo.name.lower().endswith('.xlsx'):
        return Response({'error': 'El archivo tiene que ser un Excel (.xlsx) exportado de Xubio.'}, status=400)
    if archivo.size > TAMANIO_MAX_EXCEL:
        return Response({'error': 'El archivo es demasiado grande (máximo 5 MB).'}, status=400)

    try:
        tipo, filas = leer_excel(archivo)
        plan = planificar(tipo, filas)
        confirmar = str(request.data.get('confirmar', '')).lower() == 'true'
        resumen = aplicar(plan) if confirmar else plan['resumen']
    except ErrorImportacion as e:
        return Response({'error': str(e)}, status=400)
    return Response({'aplicado': confirmar, 'resumen': resumen})


# ── Saldos bancarios (BBVA / Mercado Pago) ──────────────────────────────────
@api_view(['GET', 'POST'])
@permission_classes([EsAdmin])
def ff_saldos(request):
    if request.method == 'GET':
        ultimos = {}
        for clave, _etiqueta in models.SaldoBancario.CUENTAS:
            s = models.SaldoBancario.objects.filter(cuenta=clave).first()  # orden: fecha desc
            ultimos[clave] = _saldo_dict(s) if s else None
        historial = models.SaldoBancario.objects.all()[:60]
        return Response({'saldos': [_saldo_dict(s) for s in historial], 'ultimos': ultimos})
    try:
        cuenta = request.data.get('cuenta')
        if cuenta not in dict(models.SaldoBancario.CUENTAS):
            raise DatoInvalido('Cuenta inválida')
        s, _ = models.SaldoBancario.objects.update_or_create(
            cuenta=cuenta, fecha=_fecha(request.data.get('fecha')),
            defaults={'monto': _decimal(request.data.get('monto'), positivo=False)},
        )
    except DatoInvalido as e:
        return Response({'error': str(e)}, status=400)
    return Response(_saldo_dict(s), status=201)


@api_view(['DELETE'])
@permission_classes([EsAdmin])
def ff_saldo_detalle(request, pk):
    deleted, _ = models.SaldoBancario.objects.filter(pk=pk).delete()
    if not deleted:
        return Response({'error': 'No existe'}, status=404)
    return Response({'ok': True})