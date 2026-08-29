import requests
from datetime import date, timedelta
from django.conf import settings
import requests

XUBIO_BASE = 'https://xubio.com:443/API/1.1'
DEPOSITO_ID = -2
PROVINCIA_ID = 3
IVA = 10.5

IDENTIFICACION_TRIBUTARIA_CUIT_ID = 9

CATEGORIA_FISCAL = {
    'responsable_inscripto': 1,
    'monotributista': 4,
    'consumidor_final': 3,
}

PUNTOS_VENTA = {
    'factura': {
        'puntoVentaId': 214112,
        'circuitoContableId': 2247,
    },
    'proforma': {
        'puntoVentaId': 154275,
        'circuitoContableId': -2,
    },
}


def obtener_token():
    response = requests.post(
        f'{XUBIO_BASE}/TokenEndpoint',
        data={'grant_type': 'client_credentials'},
        auth=(settings.XUBIO_CLIENT_ID, settings.XUBIO_SECRET_ID),
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
    )
    response.raise_for_status()
    return response.json()['access_token']


def crear_cliente_en_xubio(cliente):
    token = obtener_token()
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }

    categoria_fiscal_id = CATEGORIA_FISCAL.get(cliente.condicion_iva, 3)

    payload = {
        'razonSocial': cliente.razon_social,
        'nombreComercial': cliente.nombre_comercio,
        'nombre': cliente.nombre,
        'identificacionTributaria': {'id': IDENTIFICACION_TRIBUTARIA_CUIT_ID},
        'categoriaFiscal': {'id': categoria_fiscal_id},
        'provincia': {'provincia_id': PROVINCIA_ID},
        'direccion': cliente.direccion,
        'email': cliente.mail,
        'telefono': cliente.telefono,
        'cuit': cliente.cuit,
        'CUIT': cliente.cuit,
        'esclienteextranjero': 0,
        'esProveedor': 0,
    }

    response = requests.post(
        f'{XUBIO_BASE}/clienteBean',
        json=payload,
        headers=headers,
    )

    if response.status_code in [200, 201]:
        data = response.json()
        return data.get('cliente_id') or data.get('id')
    return None


def facturar_pedido(pedido):
    token = obtener_token()
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }

    cliente = pedido.cliente
    fecha_hoy = date.today()
    fecha_vto = fecha_hoy + timedelta(days=cliente.dias_cc)

    punto_venta_key = 'factura' if cliente.xubio_tipo_comprobante == 1 else 'proforma'
    punto_venta = PUNTOS_VENTA[punto_venta_key]

    # tipo comprobante: 1=Factura, 6=Recibo
    tipo = cliente.xubio_tipo_comprobante

    items = []
    for item in pedido.itempedido_set.all():
        precio_sin_iva = float(item.precio) / 1.105
        iva_monto = float(item.precio) - precio_sin_iva
        subtotal = float(item.precio) * item.cantidad

        items.append({
            'producto': {'id': item.producto.xubio_producto_id},
            'centroDeCosto': {'id': -1},
            'deposito': {'id': DEPOSITO_ID},
            'descripcion': str(item.producto),
            'cantidad': item.cantidad,
            'precio': round(precio_sin_iva, 2),
            'precioconivaincluido': float(item.precio),
            'iva': round(iva_monto * item.cantidad, 2),
            'importe': round(precio_sin_iva * item.cantidad, 2),
            'total': round(subtotal, 2),
            'montoExento': 0,
            'porcentajeDescuento': 0,
        })

    payload = {
        'externalId': str(pedido.id),
        'cliente': {'id': cliente.xubio_cliente_id},
        'tipo': tipo,
        'nombre': f'Pedido #{pedido.id:04d}',
        'fecha': fecha_hoy.strftime('%Y-%m-%d'),
        'fechaVto': fecha_vto.strftime('%Y-%m-%d'),
        'puntoVenta': {'id': punto_venta['puntoVentaId']},
        'circuitoContable': {'id': punto_venta['circuitoContableId']},
        'numeroDocumento': cliente.cuit,
        'condicionDePago': 1,
        'deposito': {'id': DEPOSITO_ID},
        'cantComprobantesEmitidos': 1,
        'cantComprobantesCancelados': 0,
        'cotizacion': 1,
        'provincia': {'provincia_id': PROVINCIA_ID},
        'cotizacionListaDePrecio': 1,
        'listaDePrecio': {'id': -1},
        'vendedor': {'vendedorId': -1},
        'porcentajeComision': 0,
        'mailEstado': '',
        'descripcion': f'Pedido Brot Panes #{pedido.id:04d}',
        'cbuinformada': False,
        'facturaNoExportacion': True,
        'transaccionProductoItems': items,
        'transaccionPercepcionItems': [],
        'transaccionCobranzaItems': [],
    }

    response = requests.post(
        f'{XUBIO_BASE}/comprobanteVentaBean',
        json=payload,
        headers=headers,
    )

    return response.status_code, response.json()