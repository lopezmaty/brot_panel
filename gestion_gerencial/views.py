from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from users.permissions import EsAdmin
from sistema_pedidos.xubio import obtener_compras_mes, obtener_ventas_mes
from . import models


def normalizar(texto):
    return (texto or '').strip().upper()


def resolver_rubro(proveedor, producto):
    proveedor_norm = normalizar(proveedor)
    producto_norm = normalizar(producto)

    regla = models.ReglaCategorizacionMapa.objects.filter(
        proveedor__iexact=proveedor_norm, producto__iexact=producto_norm
    ).first()
    if regla:
        return regla.rubro

    regla = models.ReglaCategorizacionMapa.objects.filter(
        proveedor__iexact=proveedor_norm, producto='*'
    ).first()
    if regla:
        return regla.rubro

    return models.SIN_CATEGORIZAR


def _rango_fechas(mes):
    anio_str, mes_str = mes.split('-')
    anio, mes_num = int(anio_str), int(mes_str)
    fecha_desde = f'{anio:04d}-{mes_num:02d}-01'
    if mes_num == 12:
        fecha_hasta = f'{anio + 1:04d}-01-01'
    else:
        fecha_hasta = f'{anio:04d}-{mes_num + 1:02d}-01'
    return fecha_desde, fecha_hasta


@api_view(['POST'])
@permission_classes([EsAdmin])
def importar_compras_xubio(request):
    mes = request.data.get('mes')
    if not mes:
        return Response({'error': 'Falta el mes (formato YYYY-MM).'}, status=400)

    try:
        fecha_desde, fecha_hasta = _rango_fechas(mes)
    except (ValueError, AttributeError):
        return Response({'error': 'Formato de mes inválido, usá YYYY-MM.'}, status=400)

    try:
        lineas = obtener_compras_mes(fecha_desde, fecha_hasta)
    except Exception as e:
        return Response({'error': f'Error consultando Xubio: {e}'}, status=500)

    importadas = 0
    sin_categorizar = 0

    for linea in lineas:
        rubro = resolver_rubro(linea['proveedor'], linea['producto'])
        if rubro == models.SIN_CATEGORIZAR:
            sin_categorizar += 1

        models.CompraMapa.objects.update_or_create(
            mes=mes,
            xubio_transaccion_id=linea['transaccion_id'],
            xubio_item_id=linea['item_id'],
            defaults={
                'fecha': linea['fecha'] or None,
                'documento': linea['documento'] or '',
                'proveedor': linea['proveedor'],
                'producto': linea['producto'],
                'descripcion': linea['descripcion'] or '',
                'importe': linea['importe'] or 0,
                'rubro': rubro,
            }
        )
        importadas += 1

    return Response({
        'importadas': importadas,
        'sin_categorizar': sin_categorizar,
    })


@api_view(['POST'])
@permission_classes([EsAdmin])
def importar_ventas_xubio(request):
    mes = request.data.get('mes')
    if not mes:
        return Response({'error': 'Falta el mes (formato YYYY-MM).'}, status=400)

    try:
        fecha_desde, fecha_hasta = _rango_fechas(mes)
    except (ValueError, AttributeError):
        return Response({'error': 'Formato de mes inválido, usá YYYY-MM.'}, status=400)

    try:
        datos = obtener_ventas_mes(fecha_desde, fecha_hasta)
    except Exception as e:
        return Response({'error': f'Error consultando Xubio: {e}'}, status=500)

    models.DatosMesMapa.objects.update_or_create(
        mes=mes,
        defaults={
            'ventas_netas': datos['ventas_netas'],
            'unidades': datos['unidades'],
            'clientes_activos': datos['clientes_activos'],
            'clientes_80': datos['clientes_80'],
            'productos_80': datos['productos_80'],
        }
    )

    models.VentaClienteMapa.objects.filter(mes=mes).delete()
    models.VentaClienteMapa.objects.bulk_create([
        models.VentaClienteMapa(
            mes=mes, cliente=c['cliente'], importe=c['importe'], cantidad=c['cantidad']
        ) for c in datos['clientes']
    ])

    models.VentaProductoMapa.objects.filter(mes=mes).delete()
    models.VentaProductoMapa.objects.bulk_create([
        models.VentaProductoMapa(
            mes=mes, producto=p['producto'], importe=p['importe'], cantidad=p['cantidad']
        ) for p in datos['productos']
    ])

    return Response({
        'ventas_netas': datos['ventas_netas'],
        'unidades': datos['unidades'],
        'clientes_activos': datos['clientes_activos'],
        'clientes_80': datos['clientes_80'],
        'productos_80': datos['productos_80'],
    })


@api_view(['GET'])
@permission_classes([EsAdmin])
def listar_compras_mes(request):
    mes = request.GET.get('mes')
    if not mes:
        return Response({'error': 'Falta el mes.'}, status=400)

    solo_sin_categorizar = request.GET.get('solo_sin_categorizar') == '1'
    rubro = request.GET.get('rubro')

    compras = models.CompraMapa.objects.filter(mes=mes).order_by('proveedor', 'producto')
    if solo_sin_categorizar:
        compras = compras.filter(rubro=models.SIN_CATEGORIZAR)
    elif rubro:
        compras = compras.filter(rubro=rubro)

    data = [
        {
            'id': c.id,
            'proveedor': c.proveedor,
            'producto': c.producto,
            'descripcion': c.descripcion,
            'importe': str(c.importe),
            'rubro': c.rubro,
            'fecha': c.fecha.isoformat() if c.fecha else None,
            'documento': c.documento,
        }
        for c in compras
    ]
    return Response(data)


@api_view(['POST'])
@permission_classes([EsAdmin])
def asignar_rubro_compra(request):
    compra_id = request.data.get('compra_id')
    rubro = request.data.get('rubro')
    recordar = request.data.get('recordar', False)
    alcance = request.data.get('alcance', 'producto')

    if not compra_id or not rubro:
        return Response({'error': 'Faltan datos.'}, status=400)

    try:
        compra = models.CompraMapa.objects.get(id=compra_id)
    except models.CompraMapa.DoesNotExist:
        return Response({'error': 'Compra no encontrada.'}, status=404)

    compra.rubro = rubro
    compra.save(update_fields=['rubro'])

    if recordar:
        producto_regla = '*' if alcance == 'proveedor' else compra.producto
        models.ReglaCategorizacionMapa.objects.update_or_create(
            proveedor=compra.proveedor,
            producto=producto_regla,
            defaults={'rubro': rubro},
        )

    return Response({'ok': True})


@api_view(['GET'])
@permission_classes([EsAdmin])
def obtener_datos_mes(request):
    mes = request.GET.get('mes')
    if not mes:
        return Response({'error': 'Falta el mes.'}, status=400)

    try:
        datos = models.DatosMesMapa.objects.get(mes=mes)
        return Response({
            'ventas_netas': str(datos.ventas_netas),
            'unidades': datos.unidades,
            'clientes_activos': datos.clientes_activos,
            'clientes_80': datos.clientes_80,
            'productos_80': datos.productos_80,
            'observaciones': datos.observaciones,
        })
    except models.DatosMesMapa.DoesNotExist:
        return Response({
            'ventas_netas': '0',
            'unidades': 0,
            'clientes_activos': 0,
            'clientes_80': 0,
            'productos_80': 0,
            'observaciones': '',
        })


@api_view(['POST'])
@permission_classes([EsAdmin])
def guardar_datos_mes(request):
    mes = request.data.get('mes')
    if not mes:
        return Response({'error': 'Falta el mes.'}, status=400)

    models.DatosMesMapa.objects.update_or_create(
        mes=mes,
        defaults={
            'ventas_netas': request.data.get('ventas_netas') or 0,
            'unidades': request.data.get('unidades') or 0,
            'clientes_activos': request.data.get('clientes_activos') or 0,
            'clientes_80': request.data.get('clientes_80') or 0,
            'productos_80': request.data.get('productos_80') or 0,
            'observaciones': request.data.get('observaciones') or '',
        }
    )
    return Response({'ok': True})


@api_view(['GET'])
@permission_classes([EsAdmin])
def ventas_detalle_mes(request):
    mes = request.GET.get('mes')
    if not mes:
        return Response({'error': 'Falta el mes.'}, status=400)

    clientes = list(models.VentaClienteMapa.objects.filter(mes=mes).order_by('-importe').values('cliente', 'importe', 'cantidad'))
    productos = list(models.VentaProductoMapa.objects.filter(mes=mes).order_by('-importe').values('producto', 'importe', 'cantidad'))

    return Response({
        'clientes': [{'cliente': c['cliente'], 'importe': str(c['importe']), 'cantidad': c['cantidad']} for c in clientes],
        'productos': [{'producto': p['producto'], 'importe': str(p['importe']), 'cantidad': p['cantidad']} for p in productos],
    })


def _totales_por_rubro(mes):
    totales = {r['id']: 0 for r in models.RUBROS_MAPA}
    for f in models.FUERA_OPERATIVA_MAPA:
        totales[f['id']] = 0
    totales[models.SIN_CATEGORIZAR] = 0

    for compra in models.CompraMapa.objects.filter(mes=mes):
        totales[compra.rubro] = totales.get(compra.rubro, 0) + float(compra.importe)

    return totales


@api_view(['GET'])
@permission_classes([EsAdmin])
def dashboard_mes(request):
    mes = request.GET.get('mes')
    if not mes:
        return Response({'error': 'Falta el mes.'}, status=400)

    try:
        datos_mes = models.DatosMesMapa.objects.get(mes=mes)
        ventas_netas = float(datos_mes.ventas_netas)
        unidades = datos_mes.unidades
        clientes_activos = datos_mes.clientes_activos
    except models.DatosMesMapa.DoesNotExist:
        ventas_netas = 0
        unidades = 0
        clientes_activos = 0

    tot = _totales_por_rubro(mes)
    sin_cat_monto = tot.get(models.SIN_CATEGORIZAR, 0)
    sin_cat_n = models.CompraMapa.objects.filter(mes=mes, rubro=models.SIN_CATEGORIZAR).count()

    compras_operativas = sum(tot.get(r['id'], 0) for r in models.RUBROS_MAPA)
    total_fuera_op = sum(tot.get(f['id'], 0) for f in models.FUERA_OPERATIVA_MAPA)
    total_facturado = compras_operativas + total_fuera_op + sin_cat_monto

    margen = (ventas_netas - compras_operativas) if ventas_netas else None
    margen_pct = (margen / ventas_netas) if ventas_netas else None
    compras_ventas_pct = (compras_operativas / ventas_netas) if ventas_netas else None

    return Response({
        'ventas_netas': ventas_netas,
        'unidades': unidades,
        'clientes_activos': clientes_activos,
        'totales_por_rubro': tot,
        'sin_categorizar_monto': sin_cat_monto,
        'sin_categorizar_n': sin_cat_n,
        'compras_operativas': compras_operativas,
        'total_fuera_operativa': total_fuera_op,
        'total_facturado': total_facturado,
        'margen': margen,
        'margen_pct': margen_pct,
        'compras_ventas_pct': compras_ventas_pct,
    })


@api_view(['GET'])
@permission_classes([EsAdmin])
def historico(request):
    meses_compras = set(models.CompraMapa.objects.values_list('mes', flat=True).distinct())
    meses_ventas = set(models.DatosMesMapa.objects.values_list('mes', flat=True).distinct())
    meses = sorted(meses_compras | meses_ventas)

    filas = []
    for mes in meses:
        tot = _totales_por_rubro(mes)
        compras_operativas = sum(tot.get(r['id'], 0) for r in models.RUBROS_MAPA)
        try:
            datos_mes = models.DatosMesMapa.objects.get(mes=mes)
            ventas_netas = float(datos_mes.ventas_netas)
            unidades = datos_mes.unidades
            clientes_activos = datos_mes.clientes_activos
        except models.DatosMesMapa.DoesNotExist:
            ventas_netas = 0
            unidades = 0
            clientes_activos = 0

        margen = (ventas_netas - compras_operativas) if ventas_netas else None
        margen_pct = (margen / ventas_netas) if ventas_netas else None
        compras_ventas_pct = (compras_operativas / ventas_netas) if ventas_netas else None

        filas.append({
            'mes': mes,
            'ventas_netas': ventas_netas,
            'unidades': unidades,
            'clientes_activos': clientes_activos,
            'compras_operativas': compras_operativas,
            'margen': margen,
            'margen_pct': margen_pct,
            'compras_ventas_pct': compras_ventas_pct,
        })

    return Response(filas)


@login_required(login_url='login')
def mapa_economico_view(request):
    if request.user.perfil.rol != 'admin':
        return redirect('dashboard')

    rubros = []
    for r in models.RUBROS_MAPA:
        rango_txt = f"{int(r['verde_min']*100)}% a {int(r['verde_max']*100)}%"
        rubros.append({**r, 'rango_txt': rango_txt})

    return render(request, 'mapa_economico.html', {
        'rubros_json': rubros,
        'fuera_operativa_json': models.FUERA_OPERATIVA_MAPA,
    })

@api_view(['POST'])
@permission_classes([EsAdmin])
def importar_precios_costeo(request):
    from sistema_pedidos.xubio import obtener_precios_lista
    from .models import ProductoCosteo, XUBIO_LISTA_GASTRONOMICO_ID, XUBIO_LISTA_DISTRIBUIDOR_ID, HistorialPrecioCosteo

    # Construir índice xubio_id → producto
    productos = {
        p.xubio_producto_id: p
        for p in ProductoCosteo.objects.filter(xubio_producto_id__isnull=False)
    }

    items_gastronomico = obtener_precios_lista(XUBIO_LISTA_GASTRONOMICO_ID)
    items_distribuidor = obtener_precios_lista(XUBIO_LISTA_DISTRIBUIDOR_ID)

    actualizados = []

    for item in items_gastronomico:
        xubio_id = item['producto']['id']
        precio_nuevo = item.get('precio') or 0
        if not precio_nuevo or xubio_id not in productos:
            continue
        prod = productos[xubio_id]
        precio_anterior = prod.precio_con_iva
        if precio_anterior != precio_nuevo:
            HistorialPrecioCosteo.objects.create(
                tipo='gastronomico',
                item=prod.nombre,
                valor_anterior=precio_anterior,
                valor_nuevo=precio_nuevo,
            )
        prod.precio_con_iva = precio_nuevo
        prod.precio_actual = round(precio_nuevo / (1 + 0.105), 2)
        prod.save(update_fields=['precio_con_iva', 'precio_actual'])
        actualizados.append({'producto': prod.nombre, 'tipo': 'gastronomico', 'precio': precio_nuevo})

    for item in items_distribuidor:
        xubio_id = item['producto']['id']
        precio_nuevo = item.get('precio') or 0
        if not precio_nuevo or xubio_id not in productos:
            continue
        prod = productos[xubio_id]
        precio_anterior = prod.precio_distribuidor or 0
        if precio_anterior != precio_nuevo:
            HistorialPrecioCosteo.objects.create(
                tipo='distribuidor',
                item=prod.nombre,
                valor_anterior=precio_anterior,
                valor_nuevo=precio_nuevo,
            )
        prod.precio_distribuidor = precio_nuevo
        prod.save(update_fields=['precio_distribuidor'])
        actualizados.append({'producto': prod.nombre, 'tipo': 'distribuidor', 'precio': precio_nuevo})

    return Response({'actualizados': len(actualizados), 'detalle': actualizados})


# ============================================================
# COSTEO Y PRECIOS — vistas de API
# ============================================================

from .services_costeo import calcular_todo


@api_view(['GET'])
@permission_classes([EsAdmin])
def costeo_calculos(request):
    """Devuelve matriz, ranking y lista de precios calculados en Python."""
    resultado = calcular_todo()
    # Convertir Decimal a float para JSON
    import decimal

    def decimal_a_float(obj):
        if isinstance(obj, dict):
            return {k: decimal_a_float(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [decimal_a_float(i) for i in obj]
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        return obj

    return Response(decimal_a_float(resultado))


@api_view(['GET'])
@permission_classes([EsAdmin])
def costeo_productos(request):
    from .models import ProductoCosteo
    productos = ProductoCosteo.objects.prefetch_related('receta__insumo', 'mano_obra').all()
    data = []
    for p in productos:
        mo = getattr(p, 'mano_obra', None)
        data.append({
            'id': p.id,
            'codigo': p.codigo,
            'nombre': p.nombre,
            'familia': p.familia,
            'peso': float(p.peso) if p.peso else None,
            'precio_actual': float(p.precio_actual),
            'precio_con_iva': float(p.precio_con_iva),
            'precio_distribuidor': float(p.precio_distribuidor) if p.precio_distribuidor else None,
            'unidades_mes': p.unidades_mes,
            'unidades_lote': p.unidades_lote,
            'margen_objetivo': float(p.margen_objetivo) if p.margen_objetivo else None,
            'descuento_objetivo': float(p.descuento_objetivo) if p.descuento_objetivo else None,
            'receta': [{
                'insumo_nombre': linea.insumo.nombre,
                'categoria': linea.categoria,
                'unidad': linea.unidad,
                'cantidad': float(linea.cantidad),
                'merma': float(linea.merma),
            } for linea in p.receta.select_related('insumo').all()],
            'mano_obra': {
                'proceso': mo.proceso,
                'personas': float(mo.personas),
                'tiempo_min_lote': float(mo.tiempo_min_lote),
            } if mo else None,
        })
    return Response(data)


@api_view(['POST'])
@permission_classes([EsAdmin])
def costeo_productos_bulk_update(request):
    from .models import ProductoCosteo
    cambios = request.data.get('cambios', [])
    campos_permitidos = {'unidades_mes', 'unidades_lote'}
    for cambio in cambios:
        field = cambio.get('field')
        if field not in campos_permitidos:
            continue
        ProductoCosteo.objects.filter(id=cambio['id']).update(**{field: cambio['value']})
    return Response({'ok': True})


@api_view(['GET'])
@permission_classes([EsAdmin])
def costeo_insumos(request):
    from .models import InsumoCosteo
    insumos = InsumoCosteo.objects.all()
    data = [{
        'id': i.id,
        'nombre': i.nombre,
        'unidad': i.unidad,
        'precio': float(i.precio),
        'comentario': i.comentario,
    } for i in insumos]
    return Response(data)


@api_view(['POST'])
@permission_classes([EsAdmin])
def costeo_insumos_bulk_update(request):
    from .models import InsumoCosteo, HistorialPrecioCosteo
    cambios = request.data.get('cambios', [])
    for cambio in cambios:
        try:
            insumo = InsumoCosteo.objects.get(id=cambio['id'])
            nuevo = float(cambio['precio'])
            if float(insumo.precio) != nuevo:
                HistorialPrecioCosteo.objects.create(
                    tipo='insumo',
                    item=insumo.nombre,
                    valor_anterior=insumo.precio,
                    valor_nuevo=nuevo,
                )
            insumo.precio = nuevo
            insumo.save(update_fields=['precio'])
        except InsumoCosteo.DoesNotExist:
            pass
    return Response({'ok': True})


@api_view(['GET', 'PATCH'])
@permission_classes([EsAdmin])
def costeo_config(request):
    from .models import ConfiguracionCosteo
    config, _ = ConfiguracionCosteo.objects.get_or_create(id=1)
    if request.method == 'GET':
        campos = [
            'sueldos_productivos', 'horas_disponibles', 'margen_minimo',
            'energia', 'mantenimiento', 'limpieza', 'sueldos_indirectos',
            'resto', 'aguinaldos', 'alquiler', 'muni', 'iva', 'ganancias', 'contador',
        ]
        return Response({campo: float(getattr(config, campo)) for campo in campos})
    # PATCH
    campos_permitidos = {
        'sueldos_productivos', 'horas_disponibles', 'margen_minimo',
        'energia', 'mantenimiento', 'limpieza', 'sueldos_indirectos',
        'resto', 'aguinaldos', 'alquiler', 'muni', 'iva', 'ganancias', 'contador',
    }
    for campo, valor in request.data.items():
        if campo in campos_permitidos:
            setattr(config, campo, valor)
    config.save()
    return Response({'ok': True})


@api_view(['GET'])
@permission_classes([EsAdmin])
def costeo_equipos(request):
    from .models import EquipoCosteo
    equipos = EquipoCosteo.objects.all()
    data = [{
        'id': e.id,
        'nombre': e.nombre,
        'valor_reposicion': float(e.valor_reposicion),
        'vida_util_anios': e.vida_util_anios,
    } for e in equipos]
    return Response(data)


@api_view(['POST'])
@permission_classes([EsAdmin])
def costeo_equipos_bulk_update(request):
    from .models import EquipoCosteo
    cambios = request.data.get('cambios', [])
    campos_permitidos = {'valor_reposicion', 'vida_util_anios'}
    for cambio in cambios:
        field = cambio.get('field')
        if field not in campos_permitidos:
            continue
        EquipoCosteo.objects.filter(id=cambio['id']).update(**{field: cambio['value']})
    return Response({'ok': True})

def costeo_precios_view(request):
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'admin':
        return redirect('dashboard')
    return render(request, 'costeo_precios.html')

@api_view(['GET'])
@permission_classes([EsAdmin])
def costeo_historial(request):
    from .models import HistorialPrecioCosteo
    historial = HistorialPrecioCosteo.objects.all()[:200]
    data = [{
        'id': h.id,
        'fecha': h.fecha.isoformat(),
        'tipo': h.tipo,
        'item': h.item,
        'valor_anterior': float(h.valor_anterior),
        'valor_nuevo': float(h.valor_nuevo),
    } for h in historial]
    return Response(data)


@api_view(['POST'])
@permission_classes([EsAdmin])
def costeo_mano_obra_bulk_update(request):
    from .models import ManoObraCosteo, ProductoCosteo
    cambios = request.data.get('cambios', [])
    for cambio in cambios:
        try:
            prod = ProductoCosteo.objects.get(codigo=cambio['codigo'])
            mo, _ = ManoObraCosteo.objects.get_or_create(producto=prod)
            mo.proceso = cambio.get('proceso', '')
            mo.personas = cambio.get('personas', 1)
            mo.tiempo_min_lote = cambio.get('tiempo_min_lote', 0)
            mo.save()
        except ProductoCosteo.DoesNotExist:
            pass
    return Response({'ok': True})