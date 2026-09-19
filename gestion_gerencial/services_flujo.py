import calendar
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Count, Q, Sum

from .models import CuentaCorrienteItem, SaldoBancario

CERO = Decimal('0')


def ultimo_dia_del_mes(mes: str) -> date:
    """'2026-09' -> date(2026, 9, 30)"""
    anio, m = (int(x) for x in mes.split('-'))
    return date(anio, m, calendar.monthrange(anio, m)[1])


def _efectivo_al(corte: date) -> Decimal:
    """Efectivo teórico según Control de caja: saldo inicial + movimientos
    completos hasta la fecha. Import local para no acoplar los módulos al arrancar."""
    from control_caja.views import _saldo_teorico_dia
    return Decimal(str(_saldo_teorico_dia(corte)))


def _saldo_banco(cuenta: str, corte: date):
    s = SaldoBancario.objects.filter(cuenta=cuenta, fecha__lte=corte).order_by('-fecha').first()
    return (s.monto, s.fecha) if s else (CERO, None)


def _suma(desde=None, hasta=None):
    """Sum('importe') filtrado por vencimiento. desde exclusivo, hasta inclusivo."""
    q = Q()
    if desde is not None:
        q &= Q(fecha_vencimiento__gt=desde)
    if hasta is not None:
        q &= Q(fecha_vencimiento__lte=hasta)
    return Sum('importe', filter=q)


def _fila(nombre, grupo, nota, saldo, cobros=(CERO, CERO, CERO), pagos=(CERO, CERO, CERO)):
    c30, c60, c90 = cobros
    p30, p60, p90 = pagos
    pos30 = saldo + c30 - p30
    pos60 = pos30 + c60 - p60
    pos90 = pos60 + c90 - p90
    return {
        'nombre': nombre, 'grupo': grupo, 'nota': nota, 'saldo': saldo,
        'cobros_30': c30, 'pagos_30': p30, 'pos_30': pos30,
        'cobros_60': c60, 'pagos_60': p60, 'pos_60': pos60,
        'cobros_90': c90, 'pagos_90': p90, 'pos_90': pos90,
    }


def calcular_flujo(corte: date) -> dict:
    d30, d60, d90 = (corte + timedelta(days=n) for n in (30, 60, 90))

    # ── Cuentas corrientes: una query, agrupada por tipo ────────────────────
    pendientes = CuentaCorrienteItem.objects.filter(estado='pendiente')
    agg = {
        f['tipo']: f
        for f in pendientes.order_by().values('tipo').annotate(
            venc=_suma(hasta=corte), n_venc=Count('id', filter=Q(fecha_vencimiento__lte=corte)),
            v30=_suma(corte, d30), v60=_suma(d30, d60), v90=_suma(d60, d90),
        )
    }
    cli, pro = agg.get('cliente', {}), agg.get('proveedor', {})
    g = lambda d, k: d.get(k) or CERO  # noqa: E731  (None -> 0)

    # ── Filas del mapa de dinero ────────────────────────────────────────────
    matriz = [_fila('Efectivo', 'disponible', 'Control de caja', _efectivo_al(corte))]
    for clave, etiqueta in SaldoBancario.CUENTAS:
        monto, fecha = _saldo_banco(clave, corte)
        nota = f'Saldo cargado al {fecha.strftime("%d/%m/%Y")}' if fecha else 'Sin saldo cargado'
        matriz.append(_fila(etiqueta, 'disponible', nota, monto))
    matriz.append(_fila(
        'Cuenta corriente clientes', 'cobrar', 'Vencido al corte + cobros por vencimiento', g(cli, 'venc'),
        cobros=(g(cli, 'v30'), g(cli, 'v60'), g(cli, 'v90'))))
    matriz.append(_fila(
        'Cuenta corriente proveedores', 'pagar', 'Vencido al corte + pagos por vencimiento', -g(pro, 'venc'),
        pagos=(g(pro, 'v30'), g(pro, 'v60'), g(pro, 'v90'))))

    posicion_corte = sum((m['saldo'] for m in matriz), CERO)
    kpis = {
        'disponibilidad': sum((m['saldo'] for m in matriz if m['grupo'] == 'disponible'), CERO),
        'vencido_cobrar': g(cli, 'venc'),
        'vencido_pagar': g(pro, 'venc'),
        'vencidos_cobrar_n': cli.get('n_venc', 0),
        'vencidos_pagar_n': pro.get('n_venc', 0),
        'posicion_corte': posicion_corte,
        'posicion_30': sum((m['pos_30'] for m in matriz), CERO),
        'cobros_90': g(cli, 'v30') + g(cli, 'v60') + g(cli, 'v90'),
        'pagos_90': g(pro, 'v30') + g(pro, 'v60') + g(pro, 'v90'),
    }

    # ── 13 semanas desde el día siguiente al corte ──────────────────────────
    inicio = corte + timedelta(days=1)
    semanas = [
        {'n': i + 1, 'desde': inicio + timedelta(days=7 * i),
         'hasta': inicio + timedelta(days=7 * i + 6), 'cobros': CERO, 'pagos': CERO}
        for i in range(13)
    ]
    items = pendientes.filter(
        fecha_vencimiento__gte=inicio, fecha_vencimiento__lte=inicio + timedelta(days=90)
    ).values_list('tipo', 'fecha_vencimiento', 'importe')
    for tipo, fecha, importe in items:
        semanas[(fecha - inicio).days // 7]['cobros' if tipo == 'cliente' else 'pagos'] += importe

    acumulada = posicion_corte
    for s in semanas:
        s['neto'] = s['cobros'] - s['pagos']
        acumulada += s['neto']
        s['acumulada'] = acumulada
        s['lectura'] = 'deficit' if acumulada < 0 else ('negativa' if s['neto'] < 0 else 'ok')

    return {'corte': corte, 'kpis': kpis, 'matriz': matriz, 'semanas': semanas}