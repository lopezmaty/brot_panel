import requests
from datetime import date, timedelta
from django.conf import settings

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

LETRA_COMPROBANTE = {
    'responsable_inscripto': 'A',
    'monotributista': 'B',
    'consumidor_final': 'B',
}

PUNTOS_VENTA = {
    'factura': {
        'puntoVentaId': 214112,
        'puntoVentaNumero': '00003',
    },
    'proforma': {
        'puntoVentaId': 154275,
        'puntoVentaNumero': '09999',
    },
}

NOMBRE_COMPROBANTE = {
    1: 'Factura',
    6: 'Recibo',
}

PRODUCTOS_EXCLUIDOS_VENTAS = {
    'ENVIO 1',
    'ENVIO 2',
    'ENVIO ESPECIAL',
    'ENVIO MERCADO',
    'ENVIO SIN CARGO',
    'PACKAGING',
    'PANES VARIOS',
    'SALDO AL INICIO',
    'PRODUCTO AL 21%',
    'SERVICIO AL 21%',
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


def obtener_proximo_numero_comprobante(punto_venta_numero, letra):
    token = obtener_token()
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json',
    }
    response = requests.get(
        f'{XUBIO_BASE}/talonario',
        params={'puntoDeVenta': punto_venta_numero},
        headers=headers,
    )
    response.raise_for_status()
    talonarios = response.json()

    tipo_buscado = f'Facturas de Venta {letra}'
    for talonario in talonarios:
        if talonario.get('tipoComprobante') == tipo_buscado:
            ultimo = int(talonario.get('ultimoUtilizado', '0'))
            return str(ultimo + 1).zfill(8)

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

    punto_venta_key = 'proforma' if cliente.xubio_punto_venta_id == 154275 else 'factura'
    punto_venta = PUNTOS_VENTA[punto_venta_key]

    tipo = cliente.xubio_tipo_comprobante
    nombre_comprobante = NOMBRE_COMPROBANTE.get(tipo, 'Factura')

    letra = LETRA_COMPROBANTE.get(cliente.condicion_iva, 'B')
    numero_documento = obtener_proximo_numero_comprobante(punto_venta['puntoVentaNumero'], letra)

    if numero_documento is None:
        return 400, {'error': f'No se encontró talonario para Facturas de Venta {letra} en el punto de venta {punto_venta["puntoVentaNumero"]}'}

    items = []
    for item in pedido.itempedido_set.all():
        precio_sin_iva = float(item.precio) / 1.105
        iva_monto = float(item.precio) - precio_sin_iva
        subtotal = float(item.precio) * item.cantidad

        items.append({
            'producto': {
                'id': item.producto.xubio_producto_id,
                'productoid': item.producto.xubio_producto_id,
            },
            'centroDeCosto': None,
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
        'nombre': nombre_comprobante,
        'fecha': fecha_hoy.strftime('%Y-%m-%d'),
        'fechaVto': fecha_vto.strftime('%Y-%m-%d'),
        'puntoVenta': {
            'id': punto_venta['puntoVentaId'],
            'ID': punto_venta['puntoVentaId'],
            'codigo': punto_venta['puntoVentaNumero'],
        },
        'numeroDocumento': numero_documento,
        'condicionDePago': 1,
        'deposito': {'id': DEPOSITO_ID},
        'cantComprobantesEmitidos': 1,
        'cantComprobantesCancelados': 0,
        'cotizacion': 1,
        'provincia': {'provincia_id': PROVINCIA_ID},
        'vendedor': {'vendedorId': 8399},
        'porcentajeComision': 0,
        'mailEstado': '',
        'descripcion': f'Pedido Brot Panes #{pedido.id:04d}',
        'cbuinformada': False,
        'facturaNoExportacion': True,
        'transaccionProductoItems': items,
        'transaccionPercepcionItems': [],
        'transaccionCobranzaItems': [],
    }

    print(f"Xubio payload: {payload}")

    response = requests.post(
        f'{XUBIO_BASE}/comprobanteVentaBean',
        json=payload,
        headers=headers,
    )

    print(f"Xubio status: {response.status_code}")
    print(f"Xubio response: {response.text}")

    return response.status_code, response.json() if response.text else {}


def obtener_precios_lista(xubio_lista_precio_id):
    token = obtener_token()
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json',
    }

    response = requests.get(
        f'{XUBIO_BASE}/listaPrecioBean/{xubio_lista_precio_id}',
        headers=headers,
    )
    response.raise_for_status()
    data = response.json()
    return data.get('listaPrecioItem', [])


def _paginar_comprobantes(endpoint, fecha_desde, fecha_hasta, headers):
    """
    Trae comprobantes de un endpoint que pagina por lastTransactionID, ignorando
    el filtro de fechaDesde/fechaHasta del servidor (bug conocido de Xubio en modo
    paginado). Filtra por fecha del lado del cliente y corta en cuanto encuentra
    un comprobante más viejo que fecha_desde, ya que vienen ordenados del más
    nuevo al más viejo.
    """
    comprobantes = []
    last_id = None
    limit = 500

    while True:
        headers_pagina = dict(headers)
        headers_pagina['minimalVersion'] = 'true'
        headers_pagina['limit'] = str(limit)
        if last_id:
            headers_pagina['lastTransactionID'] = str(last_id)

        response = requests.get(
            endpoint,
            params={'fechaDesde': fecha_desde, 'fechaHasta': fecha_hasta},
            headers=headers_pagina,
        )
        response.raise_for_status()
        pagina = response.json()
        if not pagina:
            break

        llego_al_final = False
        for c in pagina:
            fecha_c = c.get('fecha')
            if not fecha_c:
                continue
            if fecha_c < fecha_desde:
                llego_al_final = True
                break
            if fecha_c >= fecha_hasta:
                continue
            comprobantes.append(c)

        if llego_al_final:
            break
        if len(pagina) < limit:
            break

        nuevo_last_id = pagina[-1].get('transaccionid')
        if not nuevo_last_id or nuevo_last_id == last_id:
            break
        last_id = nuevo_last_id
        if len(comprobantes) > 20000:
            break

    return comprobantes


def obtener_compras_mes(fecha_desde, fecha_hasta):
    """
    fecha_desde, fecha_hasta: strings 'YYYY-MM-DD'.
    Devuelve TODAS las líneas del rango, con el shape que espera Mapa Económico.
    Trata las Notas de Crédito de proveedor (tipo 3) como negativas, ya que son
    devoluciones que restan del total comprado.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    token = obtener_token()
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json',
    }

    comprobantes = _paginar_comprobantes(f'{XUBIO_BASE}/comprobanteCompraBean', fecha_desde, fecha_hasta, headers)

    def traer_detalle(transaccion_id):
        try:
            r = requests.get(
                f'{XUBIO_BASE}/comprobanteCompraBean/{transaccion_id}',
                headers=headers,
                timeout=10,
            )
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        return None

    ids = [c.get('transaccionid') for c in comprobantes if c.get('transaccionid')]
    lineas = []

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(traer_detalle, tid): tid for tid in ids}
        for future in as_completed(futures):
            detalle = future.result()
            if not detalle:
                continue
            proveedor = (detalle.get('proveedor') or {}).get('nombre', '')
            fecha = detalle.get('fecha')
            documento = detalle.get('numeroDocumento', '')
            transaccion_id = detalle.get('transaccionid')

            # tipo 3 = Nota de Crédito de proveedor (devolución, resta)
            signo = -1 if detalle.get('tipo') == 3 else 1

            for item in detalle.get('transaccionProductoItems', []):
                producto = (item.get('producto') or {}).get('nombre', '')
                lineas.append({
                    'transaccion_id': transaccion_id,
                    'item_id': item.get('transaccionCVItemId'),
                    'fecha': fecha,
                    'documento': documento,
                    'proveedor': proveedor,
                    'producto': producto,
                    'descripcion': item.get('descripcion', ''),
                    'importe': (item.get('importe', 0) or 0) * signo,
                })

    return lineas


def obtener_ventas_mes(fecha_desde, fecha_hasta):
    """
    fecha_desde, fecha_hasta: strings 'YYYY-MM-DD'.
    Trae TODAS las ventas del rango, agrupadas por cliente y por producto.
    Excluye ítems que no son producto real (envíos, packaging, líneas de IVA genéricas, etc.)
    y trata las Notas de Crédito (tipo 3) como negativas, ya que son devoluciones.
    Devuelve un dict con las métricas que usa el Mapa Económico.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    token = obtener_token()
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json',
    }

    comprobantes = _paginar_comprobantes(f'{XUBIO_BASE}/comprobanteVentaBean', fecha_desde, fecha_hasta, headers)

    def traer_detalle(transaccion_id):
        try:
            r = requests.get(
                f'{XUBIO_BASE}/comprobanteVentaBean/{transaccion_id}',
                headers=headers,
                timeout=10,
            )
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        return None

    ids = [c.get('transaccionid') for c in comprobantes if c.get('transaccionid')]

    clientes_agg = {}
    productos_agg = {}

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(traer_detalle, tid): tid for tid in ids}
        for future in as_completed(futures):
            detalle = future.result()
            if not detalle:
                continue

            cliente_nombre = (detalle.get('cliente') or {}).get('nombre', '') or 'Sin nombre'
            items = detalle.get('transaccionProductoItems', [])

            # tipo 3 = Nota de Crédito (devolución, resta) / cualquier otro tipo suma normal
            signo = -1 if detalle.get('tipo') == 3 else 1

            importe_comprobante = 0
            cantidad_comprobante = 0

            for item in items:
                producto_nombre = (item.get('producto') or {}).get('nombre', '') or 'Sin producto'
                if producto_nombre.strip().upper() in PRODUCTOS_EXCLUIDOS_VENTAS:
                    continue

                importe_item = float(item.get('importe') or 0) * signo
                cantidad_item = float(item.get('cantidad') or 0) * signo

                importe_comprobante += importe_item
                cantidad_comprobante += cantidad_item

                if producto_nombre not in productos_agg:
                    productos_agg[producto_nombre] = {'importe': 0, 'cantidad': 0}
                productos_agg[producto_nombre]['importe'] += importe_item
                productos_agg[producto_nombre]['cantidad'] += cantidad_item

            if cliente_nombre not in clientes_agg:
                clientes_agg[cliente_nombre] = {'importe': 0, 'cantidad': 0}
            clientes_agg[cliente_nombre]['importe'] += importe_comprobante
            clientes_agg[cliente_nombre]['cantidad'] += cantidad_comprobante

    ventas_netas = sum(c['importe'] for c in clientes_agg.values())
    unidades = sum(c['cantidad'] for c in clientes_agg.values())
    clientes_activos = len([c for c in clientes_agg.values() if c['importe'] > 0])

    clientes_ordenados = sorted(clientes_agg.items(), key=lambda x: x[1]['importe'], reverse=True)
    acumulado = 0
    clientes_80 = 0
    for nombre, datos in clientes_ordenados:
        acumulado += datos['importe']
        clientes_80 += 1
        if ventas_netas > 0 and acumulado >= ventas_netas * 0.8:
            break

    productos_ordenados = sorted(productos_agg.items(), key=lambda x: x[1]['importe'], reverse=True)
    acumulado_p = 0
    productos_80 = 0
    for nombre, datos in productos_ordenados:
        acumulado_p += datos['importe']
        productos_80 += 1
        if ventas_netas > 0 and acumulado_p >= ventas_netas * 0.8:
            break

    return {
        'ventas_netas': ventas_netas,
        'unidades': unidades,
        'clientes_activos': clientes_activos,
        'clientes_80': clientes_80,
        'productos_80': productos_80,
        'clientes': [
            {'cliente': nombre, 'importe': datos['importe'], 'cantidad': datos['cantidad']}
            for nombre, datos in clientes_ordenados
        ],
        'productos': [
            {'producto': nombre, 'importe': datos['importe'], 'cantidad': datos['cantidad']}
            for nombre, datos in productos_ordenados
        ],
    }
