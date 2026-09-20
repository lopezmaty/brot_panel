"""
Importador de los reportes "Cuentas a cobrar" y "Cuentas a pagar" de Xubio (Excel).

Cada reporte es una foto de TODO lo que está pendiente en ese momento, así que cada vez
que se sube un reporte REEMPLAZA por completo lo anterior de ese tipo (clientes o proveedores):
lo que ya no figura desaparece, lo nuevo se agrega y lo que cambió queda actualizado.
Esto incluye lo que se haya cargado a mano.

Se usa en dos pasos: planificar() muestra qué va a pasar sin tocar nada; aplicar() lo hace.
"""
import hashlib
import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import openpyxl
from django.db import transaction

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
    actuales = list(CuentaCorrienteItem.objects.filter(tipo=tipo, estado='pendiente'))
    por_ext = {i.external_id: i for i in actuales if i.external_id}
    manuales = {(_clave(i.contraparte), _clave(i.comprobante)): i
                for i in actuales if not i.external_id and i.comprobante}

    nuevos = actualizados = sin_cambios = 0
    en_archivo = set()
    for f in filas:
        item = por_ext.get(f['external_id']) or manuales.get((_clave(f['contraparte']), _clave(f['comprobante'])))
        if item is None:
            nuevos += 1
            continue
        en_archivo.add(item.pk)
        igual = (item.importe == f['importe'] and item.fecha_vencimiento == f['fecha_vencimiento']
                 and item.contraparte == f['contraparte'])
        if igual:
            sin_cambios += 1
        else:
            actualizados += 1

    desaparecen = [i for i in actuales if i.pk not in en_archivo]
    manuales_reemplazados = [i for i in desaparecen if i.origen == 'manual']

    advertencias = []
    if len(desaparecen) >= 10 and len(desaparecen) > len(actuales) / 2:
        advertencias.append(
            f'Este archivo elimina {len(desaparecen)} de {len(actuales)} comprobantes pendientes. '
            'Si exportaste el reporte con filtros (por ejemplo un solo cliente), no lo confirmes.')
    if not filas and actuales:
        advertencias.append('El archivo no tiene comprobantes: se eliminarían todos los pendientes.')

    total_archivo = sum((f['importe'] for f in filas), Decimal('0'))
    vencido_archivo = sum((f['importe'] for f in filas if f['fecha_vencimiento'] < hoy), Decimal('0'))
    resumen = {
        'tipo': tipo, 'filas': len(filas),
        'nuevos': nuevos, 'actualizados': actualizados, 'sin_cambios': sin_cambios,
        'cerrados': len(desaparecen),                       # los que ya no figuran: desaparecen
        'manuales_reemplazados': len(manuales_reemplazados),
        'total_archivo': float(total_archivo), 'vencido_archivo': float(vencido_archivo),
        'total_antes': float(sum((i.importe for i in actuales), Decimal('0'))),
        'advertencias': advertencias,
    }
    return {'tipo': tipo, 'filas': filas, 'resumen': resumen}


# ── Aplicar ──────────────────────────────────────────────────────────────────
@transaction.atomic
def aplicar(plan):
    """Reemplaza todo lo de este tipo (clientes o proveedores) por el contenido del reporte."""
    tipo = plan['tipo']
    CuentaCorrienteItem.objects.filter(tipo=tipo).delete()
    CuentaCorrienteItem.objects.bulk_create([
        CuentaCorrienteItem(
            tipo=tipo, contraparte=f['contraparte'], comprobante=f['comprobante'],
            fecha_emision=f['fecha_emision'], fecha_vencimiento=f['fecha_vencimiento'],
            importe=f['importe'], estado='pendiente', observaciones=f['doc_tipo'][:300],
            origen='import', external_id=f['external_id'])
        for f in plan['filas']
    ])
    return plan['resumen']