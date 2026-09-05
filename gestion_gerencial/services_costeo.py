from decimal import Decimal


IVA_RATE = Decimal('0.105')
TOLERANCIA_DESCUENTO = Decimal('0.02')


def _d(val, default=0):
    """Convierte cualquier valor a Decimal sin explotar."""
    if val is None:
        return Decimal(str(default))
    try:
        return Decimal(str(val))
    except Exception:
        return Decimal(str(default))


# ---------- 1. Costo de materia prima por unidad ----------
# Por cada línea de receta:
#   unidades_vendibles = unidades_lote * (1 - merma)
#   costo_linea = cantidad * precio_insumo / unidades_vendibles
# costo MP unitario = suma de todas las líneas
def calc_mp_unitario(producto):
    unidades_lote = _d(producto.unidades_lote)
    if not unidades_lote:
        return Decimal('0')

    total = Decimal('0')
    for linea in producto.receta.select_related('insumo').all():
        merma = _d(linea.merma)
        unidades_vendibles = unidades_lote * (1 - merma)
        if not unidades_vendibles:
            continue
        precio = _d(linea.insumo.precio)
        cantidad = _d(linea.cantidad)
        total += (cantidad * precio) / unidades_vendibles

    return total


# ---------- 2. Mano de obra ----------
# costoHora = sueldos_productivos / horas_disponibles
# Por producto:
#   lotes_mes = unidades_mes / unidades_lote
#   horas_activas = personas * (tiempo_min_lote / 60) * lotes_mes
# El saldo ocioso (horas_disponibles - total_horas_activas) se redistribuye
# proporcionalmente al % de horas activas de cada producto.
# costo_mo_unitario = (horas_activas + incremento_proporcional) * costoHora / unidades_mes
def calc_mano_de_obra(productos, config):
    sueldos = _d(config.sueldos_productivos)
    horas_disp = _d(config.horas_disponibles)
    costo_hora = sueldos / horas_disp if horas_disp else Decimal('0')

    rows = []
    total_horas_activas = Decimal('0')

    for prod in productos:
        mo = getattr(prod, 'mano_obra', None)
        unidades_mes = _d(prod.unidades_mes)
        unidades_lote = _d(prod.unidades_lote)
        lotes_mes = unidades_mes / unidades_lote if unidades_lote else Decimal('0')
        personas = _d(mo.personas if mo else 0)
        tiempo = _d(mo.tiempo_min_lote if mo else 0)
        horas_activas = personas * (tiempo / 60) * lotes_mes
        total_horas_activas += horas_activas
        rows.append({
            'codigo': prod.codigo,
            'lotes_mes': lotes_mes,
            'horas_activas': horas_activas,
            'unidades_mes': unidades_mes,
        })

    saldo_horas = horas_disp - total_horas_activas
    resultado = {}
    for row in rows:
        share = row['horas_activas'] / total_horas_activas if total_horas_activas else Decimal('0')
        incremento = saldo_horas * share
        nuevo_total_horas = row['horas_activas'] + incremento
        costo_total_mo = nuevo_total_horas * costo_hora
        costo_mo_unitario = costo_total_mo / row['unidades_mes'] if row['unidades_mes'] else Decimal('0')
        resultado[row['codigo']] = {
            'lotes_mes': row['lotes_mes'],
            'horas_activas': row['horas_activas'],
            'nuevo_total_horas': nuevo_total_horas,
            'costo_mo_unitario': costo_mo_unitario,
            'costo_total_mo': costo_total_mo,
        }

    return {
        'costo_hora': costo_hora,
        'total_horas_activas': total_horas_activas,
        'saldo_horas': saldo_horas,
        'por_producto': resultado,
    }


# ---------- 3. Amortización mensual de equipos ----------
# suma de valor_reposicion / vida_util_anios / 12
def calc_amortizacion_mensual(equipos):
    total = Decimal('0')
    for eq in equipos:
        anios = _d(eq.vida_util_anios)
        if not anios:
            continue
        total += _d(eq.valor_reposicion) / anios / 12
    return total


# ---------- 4. Pool total de indirectos ----------
def calc_indirectos_total(config, equipos):
    amortizacion = calc_amortizacion_mensual(equipos)
    ind = config
    total = (
        _d(ind.energia) + _d(ind.mantenimiento) + _d(ind.limpieza)
        + _d(ind.sueldos_indirectos) + _d(ind.resto) + _d(ind.aguinaldos)
        + _d(ind.alquiler) + _d(ind.muni) + _d(ind.iva)
        + _d(ind.ganancias) + _d(ind.contador)
        + amortizacion
    )
    return {'amortizacion': amortizacion, 'total': total}


# ---------- 5. Indirectos por producto ----------
# Reparto proporcional a las horas de MO de cada producto (nuevoTotalHoras)
def calc_indirectos_por_producto(productos, config, equipos, mo_result):
    ind = calc_indirectos_total(config, equipos)
    total_ind = ind['total']

    total_horas_mo = sum(
        v['nuevo_total_horas'] for v in mo_result['por_producto'].values()
    )

    resultado = {}
    for prod in productos:
        r = mo_result['por_producto'].get(prod.codigo, {})
        horas = r.get('nuevo_total_horas', Decimal('0'))
        pct = horas / total_horas_mo if total_horas_mo else Decimal('0')
        indirectos_asignados = total_ind * pct
        unidades_mes = _d(prod.unidades_mes)
        indirecto_unitario = indirectos_asignados / unidades_mes if unidades_mes else Decimal('0')
        resultado[prod.codigo] = {
            'pct_utilizacion': pct,
            'indirectos_asignados': indirectos_asignados,
            'indirecto_unitario': indirecto_unitario,
            'horas': horas,
        }

    return {'total': total_ind, 'total_horas_mo': total_horas_mo, 'por_producto': resultado}


# ---------- 6. Matriz costo-precio ----------
def calc_matriz(productos, config, equipos):
    mo = calc_mano_de_obra(productos, config)
    indirectos = calc_indirectos_por_producto(productos, config, equipos, mo)
    piso = _d(config.margen_minimo)

    filas = []
    for prod in productos:
        mp_unit = calc_mp_unitario(prod)
        mo_row = mo['por_producto'].get(prod.codigo, {})
        ind_row = indirectos['por_producto'].get(prod.codigo, {})
        mo_unit = mo_row.get('costo_mo_unitario', Decimal('0'))
        ind_unit = ind_row.get('indirecto_unitario', Decimal('0'))
        costo_total = mp_unit + mo_unit + ind_unit

        precio = _d(prod.precio_actual)
        margen_d = precio - costo_total
        margen_pct = margen_d / precio if precio else Decimal('0')

        objetivo = _d(prod.margen_objetivo) if prod.margen_objetivo is not None else margen_pct
        if objetivo < piso:
            objetivo = piso

        precio_minimo = costo_total / (1 - objetivo) if (1 - objetivo) != 0 else Decimal('0')

        if precio >= precio_minimo - 1:
            precio_sugerido = precio
        else:
            # redondear hacia arriba al múltiplo de 10 más cercano
            pm_int = int(precio_minimo)
            precio_sugerido = Decimal(str(((pm_int // 10) + 1) * 10))

        diferencia_precio = precio_sugerido - precio

        if not precio:
            estado, estado_class = 'Sin precio', 'gris'
        elif not mp_unit and not mo_unit:
            estado, estado_class = 'Pendiente costeo', 'gris'
        elif abs(margen_pct - objetivo) < Decimal('0.001'):
            estado, estado_class = 'En objetivo', 'verde'
        elif margen_pct > objetivo:
            estado, estado_class = 'Margen mejoró', 'azul'
        elif margen_pct >= objetivo - Decimal('0.05'):
            estado, estado_class = 'Cerca del objetivo', 'amarillo'
        else:
            estado, estado_class = 'Bajo objetivo', 'rojo'

        filas.append({
            'codigo': prod.codigo,
            'nombre': prod.nombre,
            'familia': prod.familia,
            'precio_actual': precio,
            'precio_con_iva': _d(prod.precio_con_iva),
            'unidades_mes': _d(prod.unidades_mes),
            'mp_unit': mp_unit,
            'mo_unit': mo_unit,
            'ind_unit': ind_unit,
            'costo_total': costo_total,
            'margen_d': margen_d,
            'margen_pct': margen_pct,
            'margen_objetivo': objetivo,
            'precio_minimo': precio_minimo,
            'precio_sugerido': precio_sugerido,
            'diferencia_precio': diferencia_precio,
            'estado': estado,
            'estado_class': estado_class,
            'ventas': precio * _d(prod.unidades_mes),
        })

    return {'filas': filas, 'mo': mo, 'indirectos': indirectos, 'piso': piso}


# ---------- 7. Ranking ----------
def calc_ranking(productos, config, equipos):
    matriz = calc_matriz(productos, config, equipos)
    filas = sorted(matriz['filas'], key=lambda f: f['ventas'], reverse=True)
    total_ventas = sum(f['ventas'] for f in filas)

    ranking = []
    for i, f in enumerate(filas):
        rank = i + 1
        ajuste_requerido = max(Decimal('0'), f['precio_sugerido'] - f['precio_actual'])
        ajuste_pct = ajuste_requerido / f['precio_actual'] if f['precio_actual'] else Decimal('0')

        if f['estado_class'] == 'rojo':
            prioridad = 'Alta'
        elif rank <= 15 and ajuste_pct >= Decimal('0.05'):
            prioridad = 'Alta'
        elif f['estado_class'] == 'amarillo':
            prioridad = 'Media'
        elif ajuste_pct >= Decimal('0.01') and rank <= 25:
            prioridad = 'Media'
        else:
            prioridad = 'Baja'

        ranking.append({
            **f,
            'rank': rank,
            'pct_ventas': f['ventas'] / total_ventas if total_ventas else Decimal('0'),
            'ajuste_requerido': ajuste_requerido,
            'ajuste_pct': ajuste_pct,
            'prioridad': prioridad,
        })

    return ranking


# ---------- 8. Lista de precios ----------
def calc_lista_precios(productos, config, equipos):
    matriz = calc_matriz(productos, config, equipos)
    prod_por_codigo = {p.codigo: p for p in productos}
    resultado = []

    for f in matriz['filas']:
        prod = prod_por_codigo[f['codigo']]
        tiene_precio_dist = prod.precio_distribuidor is not None
        precio_dist = _d(prod.precio_distribuidor) if tiene_precio_dist else Decimal('0')
        precio_dist_neto = precio_dist / (1 + IVA_RATE) if tiene_precio_dist and precio_dist else Decimal('0')

        precio_con_iva = f['precio_con_iva']
        descuento_actual = (
            (precio_con_iva - precio_dist) / precio_con_iva
            if tiene_precio_dist and precio_con_iva else None
        )

        descuento_objetivo = _d(prod.descuento_objetivo) if prod.descuento_objetivo is not None else descuento_actual
        fuera_de_objetivo = (
            abs(descuento_actual - descuento_objetivo) > TOLERANCIA_DESCUENTO
            if descuento_actual is not None and descuento_objetivo is not None else False
        )

        margen_distribuidor = (
            (precio_dist_neto - f['costo_total']) / precio_dist_neto
            if tiene_precio_dist and precio_dist_neto else None
        )

        precio_sugerido_gastronomico = f['precio_sugerido'] * (1 + IVA_RATE)
        precio_sugerido_distribuidor = (
            precio_sugerido_gastronomico * (1 - descuento_objetivo)
            if descuento_objetivo is not None else None
        )

        resultado.append({
            'codigo': f['codigo'],
            'nombre': f['nombre'],
            'familia': f['familia'],
            'costo_total': f['costo_total'],
            'precio_gastronomico': precio_con_iva,
            'margen_gastronomico': f['margen_pct'],
            'precio_sugerido_gastronomico': precio_sugerido_gastronomico,
            'precio_distribuidor': precio_dist if tiene_precio_dist else None,
            'descuento_actual': descuento_actual,
            'descuento_objetivo': descuento_objetivo,
            'fuera_de_objetivo': fuera_de_objetivo,
            'precio_sugerido_distribuidor': precio_sugerido_distribuidor,
            'margen_distribuidor': margen_distribuidor,
        })

    return resultado


# ---------- Función de entrada principal ----------
# Carga todo de la DB de una vez (evita N+1) y devuelve todos los resultados.
def calcular_todo():
    from gestion_gerencial.models import (
        ProductoCosteo, ConfiguracionCosteo, EquipoCosteo
    )
    productos = list(
        ProductoCosteo.objects.prefetch_related('receta__insumo', 'mano_obra').all()
    )
    config = ConfiguracionCosteo.objects.get(id=1)
    equipos = list(EquipoCosteo.objects.all())

    return {
        'matriz': calc_matriz(productos, config, equipos),
        'ranking': calc_ranking(productos, config, equipos),
        'lista_precios': calc_lista_precios(productos, config, equipos),
    }