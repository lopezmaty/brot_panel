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


# ============================================================
# MAPA ECONÓMICO
# ============================================================

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
    return Response({'importadas': importadas, 'sin_categorizar': sin_categorizar})


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
        models.VentaClienteMapa(mes=mes, cliente=c['cliente'], importe=c['importe'], cantidad=c['cantidad'])
        for c in datos['clientes']
    ])
    models.VentaProductoMapa.objects.filter(mes=mes).delete()
    models.VentaProductoMapa.objects.bulk_create([
        models.VentaProductoMapa(mes=mes, producto=p['producto'], importe=p['importe'], cantidad=p['cantidad'])
        for p in datos['productos']
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
    data = [{
        'id': c.id, 'proveedor': c.proveedor, 'producto': c.producto,
        'descripcion': c.descripcion, 'importe': str(c.importe), 'rubro': c.rubro,
        'fecha': c.fecha.isoformat() if c.fecha else None, 'documento': c.documento,
    } for c in compras]
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
            proveedor=compra.proveedor, producto=producto_regla,
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
            'ventas_netas': str(datos.ventas_netas), 'unidades': datos.unidades,
            'clientes_activos': datos.clientes_activos, 'clientes_80': datos.clientes_80,
            'productos_80': datos.productos_80, 'observaciones': datos.observaciones,
        })
    except models.DatosMesMapa.DoesNotExist:
        return Response({'ventas_netas': '0', 'unidades': 0, 'clientes_activos': 0,
                         'clientes_80': 0, 'productos_80': 0, 'observaciones': ''})


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
        'ventas_netas': ventas_netas, 'unidades': unidades, 'clientes_activos': clientes_activos,
        'totales_por_rubro': tot, 'sin_categorizar_monto': sin_cat_monto,
        'sin_categorizar_n': sin_cat_n, 'compras_operativas': compras_operativas,
        'total_fuera_operativa': total_fuera_op, 'total_facturado': total_facturado,
        'margen': margen, 'margen_pct': margen_pct, 'compras_ventas_pct': compras_ventas_pct,
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
            'mes': mes, 'ventas_netas': ventas_netas, 'unidades': unidades,
            'clientes_activos': clientes_activos, 'compras_operativas': compras_operativas,
            'margen': margen, 'margen_pct': margen_pct, 'compras_ventas_pct': compras_ventas_pct,
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


# ============================================================
# CENTRO DE COSTOS
# ============================================================

@api_view(['POST'])
@permission_classes([EsAdmin])
def importar_precios_costeo(request):
    from sistema_pedidos.xubio import obtener_precios_lista
    from .models import ProductoCosteo, XUBIO_LISTA_GASTRONOMICO_ID, XUBIO_LISTA_DISTRIBUIDOR_ID, HistorialPrecioCosteo

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
                tipo='gastronomico', item=prod.nombre,
                valor_anterior=precio_anterior, valor_nuevo=precio_nuevo,
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
                tipo='distribuidor', item=prod.nombre,
                valor_anterior=precio_anterior, valor_nuevo=precio_nuevo,
            )
        prod.precio_distribuidor = precio_nuevo
        prod.save(update_fields=['precio_distribuidor'])
        actualizados.append({'producto': prod.nombre, 'tipo': 'distribuidor', 'precio': precio_nuevo})

    return Response({'actualizados': len(actualizados), 'detalle': actualizados})


from .services_costeo import calcular_todo
import decimal as _decimal_module
from decimal import Decimal
from .services_costeo import calc_mp_unitario, calc_amortizacion_mensual, _d


def _decimales_a_float(obj):
    if isinstance(obj, dict):
        return {k: _decimales_a_float(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_decimales_a_float(i) for i in obj]
    if isinstance(obj, _decimal_module.Decimal):
        return float(obj)
    return obj


@api_view(['GET'])
@permission_classes([EsAdmin])
def costeo_calculos(request):
    resultado = calcular_todo()
    return Response(_decimales_a_float(resultado))


@api_view(['GET'])
@permission_classes([EsAdmin])
def costeo_productos(request):
    from .models import ProductoCosteo
    productos = ProductoCosteo.objects.prefetch_related('receta__insumo', 'mano_obra').all()
    data = []
    for p in productos:
        mo = getattr(p, 'mano_obra', None)
        data.append({
            'id': p.id, 'codigo': p.codigo, 'nombre': p.nombre, 'familia': p.familia,
            'peso': float(p.peso) if p.peso else None,
            'precio_actual': float(p.precio_actual),
            'precio_con_iva': float(p.precio_con_iva),
            'precio_distribuidor': float(p.precio_distribuidor) if p.precio_distribuidor else None,
            'unidades_mes': p.unidades_mes, 'unidades_lote': p.unidades_lote,
            'margen_objetivo': float(p.margen_objetivo) if p.margen_objetivo else None,
            'descuento_objetivo': float(p.descuento_objetivo) if p.descuento_objetivo else None,
            'receta': [{
                'insumo_nombre': linea.insumo.nombre, 'categoria': linea.categoria,
                'unidad': linea.unidad, 'cantidad': float(linea.cantidad), 'merma': float(linea.merma),
            } for linea in p.receta.select_related('insumo').all()],
            'mano_obra': {
                'proceso': mo.proceso, 'personas': float(mo.personas),
                'tiempo_min_lote': float(mo.tiempo_min_lote),
            } if mo else None,
        })
    return Response(data)


@api_view(['POST'])
@permission_classes([EsAdmin])
def costeo_productos_bulk_update(request):
    from .models import ProductoCosteo
    cambios = request.data.get('cambios', [])
    campos_permitidos = {
        'precio_con_iva', 'precio_actual', 'precio_distribuidor',
        'unidades_mes', 'unidades_lote', 'peso',
        'margen_objetivo', 'descuento_objetivo', 'nombre', 'familia',
    }
    for cambio in cambios:
        updates = {k: v for k, v in cambio.items()
                   if k in campos_permitidos and v is not None}
        if updates:
            ProductoCosteo.objects.filter(codigo=cambio['codigo']).update(**updates)
    return Response({'ok': True})


@api_view(['GET'])
@permission_classes([EsAdmin])
def costeo_insumos(request):
    from .models import InsumoCosteo
    insumos = InsumoCosteo.objects.all()
    data = [{
        'id': i.id, 'nombre': i.nombre, 'unidad': i.unidad,
        'precio': float(i.precio), 'comentario': i.comentario,
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
                    tipo='insumo', item=insumo.nombre,
                    valor_anterior=insumo.precio, valor_nuevo=nuevo,
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
    campos = [
        'sueldos_productivos', 'horas_disponibles', 'margen_minimo',
        'energia', 'mantenimiento', 'limpieza', 'sueldos_indirectos',
        'resto', 'aguinaldos', 'alquiler', 'muni', 'iva', 'ganancias', 'contador',
    ]
    if request.method == 'GET':
        return Response({campo: float(getattr(config, campo)) for campo in campos})
    for campo, valor in request.data.items():
        if campo in set(campos):
            setattr(config, campo, valor)
    config.save()
    return Response({'ok': True})


@api_view(['GET'])
@permission_classes([EsAdmin])
def costeo_equipos(request):
    from .models import EquipoCosteo
    equipos = EquipoCosteo.objects.all()
    data = [{
        'id': e.id, 'nombre': e.nombre,
        'valor_reposicion': float(e.valor_reposicion),
        'vida_util_anios': e.vida_util_anios,
    } for e in equipos]
    return Response(data)


@api_view(['POST'])
@permission_classes([EsAdmin])
def costeo_equipos_bulk_update(request):
    from .models import EquipoCosteo
    cambios = request.data.get('cambios', [])
    for cambio in cambios:
        try:
            eq = EquipoCosteo.objects.get(id=cambio['id'])
            if 'nombre' in cambio:
                eq.nombre = cambio['nombre']
            if 'valor_reposicion' in cambio:
                eq.valor_reposicion = cambio['valor_reposicion']
            if 'vida_util_anios' in cambio:
                eq.vida_util_anios = cambio['vida_util_anios']
            eq.save()
        except EquipoCosteo.DoesNotExist:
            pass
    return Response({'ok': True})


@api_view(['GET'])
@permission_classes([EsAdmin])
def costeo_historial(request):
    from .models import HistorialPrecioCosteo
    historial = HistorialPrecioCosteo.objects.all()[:200]
    data = [{
        'id': h.id, 'fecha': h.fecha.isoformat(), 'tipo': h.tipo,
        'item': h.item, 'valor_anterior': float(h.valor_anterior),
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


@api_view(['POST'])
@permission_classes([EsAdmin])
def costeo_recetas_guardar(request):
    from .models import ProductoCosteo, InsumoCosteo, RecetaLineaCosteo
    codigo = request.data.get('codigo')
    lineas = request.data.get('lineas', [])
    if not codigo:
        return Response({'error': 'Falta el código del producto.'}, status=400)
    try:
        producto = ProductoCosteo.objects.get(codigo=codigo)
    except ProductoCosteo.DoesNotExist:
        return Response({'error': 'Producto no encontrado.'}, status=404)
    RecetaLineaCosteo.objects.filter(producto=producto).delete()
    for linea in lineas:
        try:
            insumo = InsumoCosteo.objects.get(nombre=linea['insumo'])
        except InsumoCosteo.DoesNotExist:
            continue
        RecetaLineaCosteo.objects.create(
            producto=producto, insumo=insumo,
            categoria=linea.get('categoria', ''),
            unidad=linea.get('unidad', ''),
            cantidad=linea.get('cantidad', 0),
            merma=linea.get('merma', 0),
        )
    return Response({'ok': True})


def costeo_precios_view(request):
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'admin':
        return redirect('dashboard')
    return render(request, 'costeo_precios.html')


def _snapshot_costos_mes():
    from .models import ProductoCosteo, EquipoCosteo
    productos = ProductoCosteo.objects.all()
    costo_mp_unitario = {str(p.id): float(calc_mp_unitario(p)) for p in productos}
    amortizacion_mensual = float(calc_amortizacion_mensual(EquipoCosteo.objects.all()))
    calculado = _decimales_a_float(calcular_todo())
    return {
        'costo_mp_unitario': costo_mp_unitario,
        'amortizacion_mensual': amortizacion_mensual,
        'calculado_todo': calculado,
    }


@api_view(['POST'])
@permission_classes([EsAdmin])
def cerrar_mes_costeo(request):
    mes = request.data.get('mes')
    if not mes:
        return Response({'error': 'Falta el mes (formato YYYY-MM).'}, status=400)
    datos = _snapshot_costos_mes()
    filas = datos['calculado_todo']['matriz']['filas']
    resumen = {
        'total_productos': len(filas),
        'margen_promedio': (sum(f['margen_pct'] for f in filas) / len(filas)) if filas else 0,
        'productos_en_rojo': len([f for f in filas if f['estado_class'] == 'rojo']),
        'amortizacion_mensual': datos['amortizacion_mensual'],
    }
    cierre, creado = models.SnapshotCosteo.objects.update_or_create(
        mes=mes,
        defaults={'nota': f'Cierre de {mes}', 'resumen': resumen, 'snapshot': datos},
    )
    return Response({'ok': True, 'mes': mes, 'creado': creado, 'resumen': resumen})


@api_view(['GET'])
@permission_classes([EsAdmin])
def listar_cierres_costeo(request):
    cierres = models.SnapshotCosteo.objects.filter(mes__isnull=False).order_by('-mes')
    data = [{
        'mes': c.mes, 'fecha': c.fecha.isoformat(), 'resumen': c.resumen,
    } for c in cierres]
    return Response(data)


@api_view(['GET'])
@permission_classes([EsAdmin])
def obtener_cierre_costeo(request):
    mes = request.GET.get('mes')
    if not mes:
        return Response({'error': 'Falta el mes.'}, status=400)
    try:
        cierre = models.SnapshotCosteo.objects.get(mes=mes)
    except models.SnapshotCosteo.DoesNotExist:
        return Response({'error': 'Ese mes no está cerrado.'}, status=404)
    calculado = cierre.snapshot.get('calculado_todo', {})
    return Response({
        'mes': cierre.mes, 'fecha': cierre.fecha.isoformat(),
        'resumen': cierre.resumen,
        'matriz': calculado.get('matriz', {}),
        'lista_precios': calculado.get('lista_precios', []),
    })


# ============================================================
# ESTADO DE RESULTADOS (EERR)
# ============================================================

def resolver_cuenta_eerr(proveedor, producto):
    proveedor_norm = normalizar(proveedor)
    producto_norm = normalizar(producto)
    regla = models.ReglaAsignacionCuentaEERR.objects.filter(
        proveedor__iexact=proveedor_norm, producto__iexact=producto_norm
    ).select_related('cuenta').first()
    if regla:
        return regla.cuenta
    regla = models.ReglaAsignacionCuentaEERR.objects.filter(
        proveedor__iexact=proveedor_norm, producto='*'
    ).select_related('cuenta').first()
    if regla:
        return regla.cuenta
    return None


@api_view(['POST'])
@permission_classes([EsAdmin])
def importar_compras_eerr(request):
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
        cuenta = resolver_cuenta_eerr(linea['proveedor'], linea['producto'])
        if cuenta is None:
            sin_categorizar += 1
        models.CompraEERR.objects.update_or_create(
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
                'cuenta': cuenta,
            }
        )
        importadas += 1
    return Response({'importadas': importadas, 'sin_categorizar': sin_categorizar})


@api_view(['POST'])
@permission_classes([EsAdmin])
def importar_ventas_eerr(request):
    from sistema_pedidos.xubio import obtener_ventas_diarias_producto
    mes = request.data.get('mes')
    if not mes:
        return Response({'error': 'Falta el mes (formato YYYY-MM).'}, status=400)
    try:
        fecha_desde, fecha_hasta = _rango_fechas(mes)
    except (ValueError, AttributeError):
        return Response({'error': 'Formato de mes inválido, usá YYYY-MM.'}, status=400)
    try:
        lineas = obtener_ventas_diarias_producto(fecha_desde, fecha_hasta)
    except Exception as e:
        return Response({'error': f'Error consultando Xubio: {e}'}, status=500)

    models.VentaProductoEERR.objects.filter(mes=mes).delete()
    models.VentaProductoEERR.objects.bulk_create([
        models.VentaProductoEERR(
            mes=mes, fecha=l['fecha'], xubio_producto_id=l['xubio_producto_id'],
            producto=l['producto'], cantidad=l['cantidad'], importe=l['importe'],
        ) for l in lineas
    ])
    ids_con_mapeo = set(models.XubioProductoCosteoMapeo.objects.values_list('xubio_producto_id', flat=True))
    sin_mapeo = len([l for l in lineas if l['xubio_producto_id'] not in ids_con_mapeo])
    return Response({'importadas': len(lineas), 'sin_mapeo_costeo': sin_mapeo})


@api_view(['GET'])
@permission_classes([EsAdmin])
def listar_compras_eerr(request):
    mes = request.GET.get('mes')
    if not mes:
        return Response({'error': 'Falta el mes.'}, status=400)
    solo_sin_categorizar = request.GET.get('solo_sin_categorizar') == '1'
    cuenta_id = request.GET.get('cuenta_id')
    compras = models.CompraEERR.objects.filter(mes=mes).select_related('cuenta').order_by('proveedor', 'producto')
    if solo_sin_categorizar:
        compras = compras.filter(cuenta__isnull=True)
    elif cuenta_id:
        compras = compras.filter(cuenta_id=cuenta_id)
    data = [{
        'id': c.id, 'proveedor': c.proveedor, 'producto': c.producto,
        'descripcion': c.descripcion, 'importe': str(c.importe),
        'cuenta_id': c.cuenta_id,
        'cuenta': c.cuenta.cuenta if c.cuenta else None,
        'incluir_eerr': c.cuenta.incluir_eerr if c.cuenta else None,
        'fecha': c.fecha.isoformat() if c.fecha else None, 'documento': c.documento,
    } for c in compras]
    return Response(data)


@api_view(['POST'])
@permission_classes([EsAdmin])
def asignar_cuenta_compra_eerr(request):
    compra_id = request.data.get('compra_id')
    cuenta_id = request.data.get('cuenta_id')
    recordar = request.data.get('recordar', False)
    alcance = request.data.get('alcance', 'producto')
    if not compra_id or not cuenta_id:
        return Response({'error': 'Faltan datos.'}, status=400)
    try:
        compra = models.CompraEERR.objects.get(id=compra_id)
    except models.CompraEERR.DoesNotExist:
        return Response({'error': 'Compra no encontrada.'}, status=404)
    try:
        cuenta = models.PlanCuentaEERR.objects.get(id=cuenta_id)
    except models.PlanCuentaEERR.DoesNotExist:
        return Response({'error': 'Cuenta no encontrada.'}, status=404)
    compra.cuenta = cuenta
    compra.save(update_fields=['cuenta'])
    if recordar:
        producto_regla = '*' if alcance == 'proveedor' else compra.producto
        models.ReglaAsignacionCuentaEERR.objects.update_or_create(
            proveedor=compra.proveedor, producto=producto_regla,
            defaults={'cuenta': cuenta},
        )
    return Response({'ok': True})


@api_view(['GET'])
@permission_classes([EsAdmin])
def plan_cuentas_eerr(request):
    cuentas = models.PlanCuentaEERR.objects.all()
    data = [{
        'id': c.id, 'cuenta': c.cuenta, 'tipo': c.tipo,
        'linea_eerr': c.linea_eerr, 'rubro': c.rubro,
        'incluir_eerr': c.incluir_eerr, 'signo': c.signo,
    } for c in cuentas]
    return Response(data)


@api_view(['GET'])
@permission_classes([EsAdmin])
def ventas_eerr_mes(request):
    mes = request.GET.get('mes')
    if not mes:
        return Response({'error': 'Falta el mes.'}, status=400)
    ventas = models.VentaProductoEERR.objects.filter(mes=mes).order_by('fecha', 'producto')
    mapeos = {
        m.xubio_producto_id: m.producto_costeo
        for m in models.XubioProductoCosteoMapeo.objects.select_related('producto_costeo')
    }
    cierre = (
        models.SnapshotCosteo.objects
        .filter(mes__isnull=False, mes__lte=mes)
        .order_by('-mes').first()
    )
    costo_mp_unitario_por_id = cierre.snapshot.get('costo_mp_unitario', {}) if cierre else None
    data = []
    for v in ventas:
        producto_costeo = mapeos.get(v.xubio_producto_id)
        costo_unitario = None
        cmv_linea = None
        if producto_costeo and costo_mp_unitario_por_id is not None:
            costo_unitario = costo_mp_unitario_por_id.get(str(producto_costeo.id))
            if costo_unitario is not None:
                cmv_linea = float(v.cantidad) * costo_unitario
        data.append({
            'id': v.id, 'fecha': v.fecha.isoformat(),
            'xubio_producto_id': v.xubio_producto_id,
            'producto': v.producto, 'cantidad': v.cantidad,
            'importe': str(v.importe),
            'producto_costeo': producto_costeo.nombre if producto_costeo else None,
            'sin_costeo_asociado': producto_costeo is None,
            'costeo_cerrado': cierre is not None,
            'costo_unitario_mp': costo_unitario, 'cmv_linea': cmv_linea,
        })
    return Response(data)


@api_view(['GET'])
@permission_classes([EsAdmin])
def mapeos_producto_costeo(request):
    from .models import ProductoCosteo
    mapeos = models.XubioProductoCosteoMapeo.objects.select_related('producto_costeo').all()
    data = [{
        'id': m.id, 'xubio_producto_id': m.xubio_producto_id,
        'xubio_producto_nombre': m.xubio_producto_nombre,
        'producto_costeo_id': m.producto_costeo_id,
        'producto_costeo_nombre': m.producto_costeo.nombre,
    } for m in mapeos]
    ids_mapeados = {m.xubio_producto_id for m in mapeos}
    sin_mapear = list(
        models.VentaProductoEERR.objects
        .exclude(xubio_producto_id__in=ids_mapeados)
        .exclude(xubio_producto_id__isnull=True)
        .values('xubio_producto_id', 'producto').distinct()
    )
    productos_costeo = list(ProductoCosteo.objects.values('id', 'nombre', 'codigo').order_by('nombre'))
    return Response({'mapeos': data, 'sin_mapear': sin_mapear, 'productos_costeo': productos_costeo})


@api_view(['POST'])
@permission_classes([EsAdmin])
def asignar_mapeo_producto_costeo(request):
    from .models import ProductoCosteo
    xubio_producto_id = request.data.get('xubio_producto_id')
    xubio_producto_nombre = request.data.get('xubio_producto_nombre', '')
    producto_costeo_id = request.data.get('producto_costeo_id')
    if not xubio_producto_id or not producto_costeo_id:
        return Response({'error': 'Faltan datos.'}, status=400)
    try:
        producto_costeo = ProductoCosteo.objects.get(id=producto_costeo_id)
    except ProductoCosteo.DoesNotExist:
        return Response({'error': 'Producto de costeo no encontrado.'}, status=404)
    models.XubioProductoCosteoMapeo.objects.update_or_create(
        xubio_producto_id=xubio_producto_id,
        defaults={'xubio_producto_nombre': xubio_producto_nombre, 'producto_costeo': producto_costeo},
    )
    return Response({'ok': True})


def _linea_eerr_totales(mes):
    totales = {codigo: Decimal('0') for codigo, _ in models.LINEA_EERR_CHOICES}
    compras = models.CompraEERR.objects.filter(
        mes=mes, cuenta__isnull=False, cuenta__incluir_eerr=True
    ).select_related('cuenta')
    for c in compras:
        totales[c.cuenta.linea_eerr] += _d(c.importe) * c.cuenta.signo
    return totales


def _calcular_eerr_valores(mes):
    cierre = (
        models.SnapshotCosteo.objects
        .filter(mes__isnull=False, mes__lte=mes)
        .order_by('-mes').first()
    )
    if not cierre:
        return {'mes': mes, 'costeo_cerrado': False}

    costo_mp_unitario_por_id = cierre.snapshot.get('costo_mp_unitario', {})
    amortizaciones = Decimal(str(cierre.snapshot.get('amortizacion_mensual', 0)))

    ventas = models.VentaProductoEERR.objects.filter(mes=mes)
    mapeos = {
        m.xubio_producto_id: m.producto_costeo
        for m in models.XubioProductoCosteoMapeo.objects.select_related('producto_costeo')
    }
    ventas_netas = Decimal('0')
    cmv = Decimal('0')
    ventas_sin_costeo = 0

    for v in ventas:
        ventas_netas += _d(v.importe)
        producto_costeo = mapeos.get(v.xubio_producto_id)
        costo_unit = costo_mp_unitario_por_id.get(str(producto_costeo.id)) if producto_costeo else None
        if costo_unit is None:
            ventas_sin_costeo += 1
            continue
        cmv += _d(v.cantidad) * Decimal(str(costo_unit))

    margen_bruto = ventas_netas - cmv
    totales = _linea_eerr_totales(mes)
    gastos_variables = totales['gastos_variables']
    margen_contribucion = margen_bruto - gastos_variables
    mano_obra_directa = totales['mano_obra_directa']
    indirectos_productivos = totales['indirectos_productivos']
    gastos_administracion = totales['gastos_administracion']
    gastos_financieros = totales['gastos_financieros']
    impuestos = totales['impuestos']
    otros_resultados = totales['otros_resultados']
    resultado_operativo = (
        margen_contribucion - mano_obra_directa - indirectos_productivos
        - amortizaciones - gastos_administracion - gastos_financieros
        - impuestos + otros_resultados
    )

    def pct(valor):
        return float(valor / ventas_netas) if ventas_netas else 0

    return {
        'mes': mes, 'costeo_cerrado': True,
        'ventas_netas': float(ventas_netas), 'cmv': float(cmv),
        'margen_bruto': float(margen_bruto), 'margen_bruto_pct': pct(margen_bruto),
        'gastos_variables': float(gastos_variables),
        'margen_contribucion': float(margen_contribucion), 'margen_contribucion_pct': pct(margen_contribucion),
        'mano_obra_directa': float(mano_obra_directa),
        'indirectos_productivos': float(indirectos_productivos),
        'amortizaciones': float(amortizaciones),
        'gastos_administracion': float(gastos_administracion),
        'gastos_financieros': float(gastos_financieros),
        'impuestos': float(impuestos),
        'otros_resultados': float(otros_resultados),
        'resultado_operativo': float(resultado_operativo), 'resultado_operativo_pct': pct(resultado_operativo),
        'ventas_sin_costeo_asociado': ventas_sin_costeo,
    }


@api_view(['GET'])
@permission_classes([EsAdmin])
def calcular_eerr_mes(request):
    mes = request.GET.get('mes')
    if not mes:
        return Response({'error': 'Falta el mes.'}, status=400)
    resultado = _calcular_eerr_valores(mes)
    if not resultado.get('costeo_cerrado'):
        return Response({
            'mes': mes, 'costeo_cerrado': False,
            'error': f'El mes {mes} todavía no está cerrado en Centro de Costos.',
        }, status=409)
    return Response(resultado)


@api_view(['GET'])
@permission_classes([EsAdmin])
def historico_eerr(request):
    meses_compras = set(models.CompraEERR.objects.values_list('mes', flat=True).distinct())
    meses_ventas = set(models.VentaProductoEERR.objects.values_list('mes', flat=True).distinct())
    meses = sorted(meses_compras | meses_ventas)
    filas = [_calcular_eerr_valores(mes) for mes in meses]
    return Response(filas)


@login_required(login_url='login')
def estado_resultados_view(request):
    if request.user.perfil.rol != 'admin':
        return redirect('dashboard')
    return render(request, 'estado_resultados.html')