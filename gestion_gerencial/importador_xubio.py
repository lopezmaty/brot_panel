"""
Importador de los reportes "Cuentas a cobrar" y "Cuentas a pagar" de Xubio (Excel).

Cada reporte es una foto de TODO lo que está pendiente en ese momento. Al importarlo:
  - los comprobantes nuevos se crean,
  - los que ya estaban se actualizan (importe, vencimiento),
  - los que se importaron antes y ya NO figuran en el reporte se marcan como cobrados/pagados.
Los comprobantes cargados a mano no se cierran nunca por importación (solo se actualizan
si el reporte trae el mismo comprobante del mismo cliente/proveedor).

Se usa en dos pasos: planificar() muestra qué va a pasar sin tocar nada; aplicar() lo hace.
"""
import hashlib
import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import openpyxl
from django.db import transaction
from django.utils import timezone

from .models import CuentaCorrienteItem

MAX_FILAS = 5000


class ErrorImportacion(Exception):
    """Problema con el archivo, con un mensaje pensado para mostrarle al usuario."""


# ── Utilidades de texto ──────────────────────────────────────────────────────
def _texto(valor):
    return re.sub(r'\s+', ' ', str(valor if valor is not None else '')).strip()


def _clave(valor):
    return _texto(valor).casefold()


def _encabezado(valor):
    """'Importe Mon. Transacción' -> 'importe mon. transaccion'"""
    s = unicodedata.normalize('NFKD', _texto(valor))
    return ''.join(c for c in s if not unicodedata.combining(c)).lower()


def _a_fecha(valor):
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if isinstance(valor, str):
        for formato in ('%d-%m-%Y', '%d/%m/%Y', '%Y-%m-%d'):
            try:
                return datetime.strptime(valor.strip(), formato).date()
            except ValueError:
                pass
    return None


def _a_decimal(valor):
    if valor is None or valor == '':
        return None
    if isinstance(valor, str) and ',' in valor:      # formato "1.234,56"
        valor = valor.replace('.', '').replace(',', '.')
    try:
        return Decimal(str(valor)).quantize(Decimal('0.01'))
    except InvalidOperation:
        return None


# ── Lectura del Excel ────────────────────────────────────────────────────────
def leer_excel(archivo):
    """Devuelve (tipo, filas). tipo es 'cliente' o 'proveedor' según las columnas del reporte."""
    try:
        wb = openpyxl.load_workbook(archivo, data_only=True)
        filas_excel = wb.worksheets[0].iter_rows(values_only=True)
    except Exception:
        raise ErrorImportacion('No se pudo abrir el archivo. Tiene que ser un .xlsx exportado de Xubio.')

    encabezado = None
    for fila in filas_excel:
        if fila and any(c is not None and str(c).strip() for c in fila):
            encabezado = [_encabezado(c) for c in fila]
            break
    if not encabezado:
        raise ErrorImportacion('El archivo está vacío.')

    if 'cliente' in encabezado:
        tipo, col_cp = 'cliente', 'cliente'
    elif 'proveedor' in encabezado:
        tipo, col_cp = 'proveedor', 'proveedor'
    else:
        raise ErrorImportacion('No parece un reporte de Cuentas a cobrar o a pagar de Xubio: '
                               'no encontré la columna Cliente ni Proveedor.')

    col_importe = next((c for c in ('importe mon. ppal.', 'importe mon. transaccion') if c in encabezado), None)
    faltan = [n for n, ok in (('Documento', 'documento' in encabezado),
                              ('Fecha Vto.', 'fecha vto.' in encabezado),
                              ('Importe Mon. Ppal.', col_importe is not None)) if not ok]
    if faltan:
        raise ErrorImportacion(f'Al reporte le falta la columna: {", ".join(faltan)}.')

    i_doc, i_cp = encabezado.index('documento'), encabezado.index(col_cp)
    i_vto, i_imp = encabezado.index('fecha vto.'), encabezado.index(col_importe)
    i_emi = encabezado.index('fecha') if 'fecha' in encabezado else None

    acumulado = {}
    for n, fila in enumerate(filas_excel, start=2):
        if n > MAX_FILAS + 1:
            raise ErrorImportacion(f'El archivo tiene más de {MAX_FILAS} filas.')
        doc, cp = _texto(fila[i_doc]), _texto(fila[i_cp])
        importe = _a_decimal(fila[i_imp])
        if not doc or importe is None:      # renglones vacíos o de totales
            continue
        vto = _a_fecha(fila[i_vto])
        if not cp or vto is None:
            raise ErrorImportacion(f'Fila {n}: falta el {tipo} o la fecha de vencimiento.')

        m = re.match(r'^(.*?)\s*N[°º]\s*(.+)$', doc)
        doc_tipo, numero = (m.group(1).strip(), m.group(2).strip()) if m else ('', doc)
        huella = hashlib.sha1(f'{_clave(numero)}|{_clave(cp)}'.encode('utf-8')).hexdigest()
        ext_id = f'xubio-{tipo}-{huella}'

        if ext_id in acumulado:              # mismo comprobante repetido: se suma
            acumulado[ext_id]['importe'] += importe
            acumulado[ext_id]['fecha_vencimiento'] = min(acumulado[ext_id]['fecha_vencimiento'], vto)
        else:
            acumulado[ext_id] = {
                'external_id': ext_id, 'contraparte': cp[:150], 'comprobante': numero[:60],
                'doc_tipo': doc_tipo, 'fecha_emision': _a_fecha(fila[i_emi]) if i_emi is not None else None,
                'fecha_vencimiento': vto, 'importe': importe,
            }
    return tipo, list(acumulado.values())


# ── Plan (sin tocar la base) ─────────────────────────────────────────────────
def planificar(tipo, filas, hoy=None):
    hoy = hoy or date.today()
    existentes = list(CuentaCorrienteItem.objects.filter(tipo=tipo))
    por_ext = {i.external_id: i for i in existentes if i.external_id}
    manuales = {(_clave(i.contraparte), _clave(i.comprobante)): i
                for i in existentes if not i.external_id and i.comprobante}

    nuevos, actualizar, sin_cambios, en_archivo = [], [], [], set()
    for f in filas:
        item = por_ext.get(f['external_id']) or manuales.get((_clave(f['contraparte']), _clave(f['comprobante'])))
        if item is None:
            nuevos.append(f)
            continue
        en_archivo.add(item.pk)
        igual = (item.estado == 'pendiente' and item.importe == f['importe']
                 and item.fecha_vencimiento == f['fecha_vencimiento']
                 and item.external_id == f['external_id'] and item.contraparte == f['contraparte'])
        (sin_cambios if igual else actualizar).append((item, f))

    importados_pendientes = [i for i in existentes if i.origen == 'import' and i.estado == 'pendiente']
    a_cerrar = [i for i in importados_pendientes if i.pk not in en_archivo]
    manuales_no_incluidos = [i for i in existentes
                             if i.origen == 'manual' and i.estado == 'pendiente' and i.pk not in en_archivo]

    advertencias = []
    if a_cerrar and len(a_cerrar) >= 10 and len(a_cerrar) > len(importados_pendientes) / 2:
        advertencias.append(
            f'Este archivo cierra {len(a_cerrar)} de {len(importados_pendientes)} comprobantes pendientes. '
            'Si exportaste el reporte con filtros (por ejemplo un solo cliente), no lo confirmes.')
    if not filas and importados_pendientes:
        advertencias.append('El archivo no tiene comprobantes: se cerrarían todos los pendientes importados.')

    total_archivo = sum((f['importe'] for f in filas), Decimal('0'))
    vencido_archivo = sum((f['importe'] for f in filas if f['fecha_vencimiento'] < hoy), Decimal('0'))
    resumen = {
        'tipo': tipo, 'filas': len(filas),
        'nuevos': len(nuevos), 'actualizados': len(actualizar), 'sin_cambios': len(sin_cambios),
        'cerrados': len(a_cerrar), 'manuales_no_incluidos': len(manuales_no_incluidos),
        'total_archivo': float(total_archivo), 'vencido_archivo': float(vencido_archivo),
        'total_antes': float(sum((i.importe for i in importados_pendientes), Decimal('0'))),
        'advertencias': advertencias,
    }
    return {'tipo': tipo, 'nuevos': nuevos, 'actualizar': actualizar, 'sin_cambios': sin_cambios,
            'a_cerrar': a_cerrar, 'resumen': resumen, 'hoy': hoy}


# ── Aplicar ──────────────────────────────────────────────────────────────────
@transaction.atomic
def aplicar(plan):
    tipo, hoy, ahora = plan['tipo'], plan['hoy'], timezone.now()

    CuentaCorrienteItem.objects.bulk_create([
        CuentaCorrienteItem(
            tipo=tipo, contraparte=f['contraparte'], comprobante=f['comprobante'],
            fecha_emision=f['fecha_emision'], fecha_vencimiento=f['fecha_vencimiento'],
            importe=f['importe'], estado='pendiente', observaciones=f['doc_tipo'][:300],
            origen='import', external_id=f['external_id'])
        for f in plan['nuevos']
    ])

    for item, f in plan['actualizar']:
        item.contraparte, item.comprobante = f['contraparte'], f['comprobante']
        item.fecha_vencimiento, item.importe = f['fecha_vencimiento'], f['importe']
        if f['fecha_emision']:
            item.fecha_emision = f['fecha_emision']
        item.estado, item.fecha_cancelacion = 'pendiente', None
        item.origen, item.external_id = 'import', f['external_id']
        if not item.observaciones:
            item.observaciones = f['doc_tipo'][:300]
        item.save()

    # "Tocamos" los que no cambiaron para que la fecha de última importación se actualice.
    CuentaCorrienteItem.objects.filter(pk__in=[i.pk for i, _ in plan['sin_cambios']]).update(modificado_en=ahora)
    CuentaCorrienteItem.objects.filter(pk__in=[i.pk for i in plan['a_cerrar']]).update(
        estado='cancelado', fecha_cancelacion=hoy, modificado_en=ahora)
    return plan['resumen']