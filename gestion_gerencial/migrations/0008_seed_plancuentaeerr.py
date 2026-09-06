from django.db import migrations

CUENTAS = [
    # cuenta, tipo, linea_eerr, rubro, incluir_eerr, signo, descripcion
    ('Ventas productos', 'ingreso', 'ingresos_netos', 'Ingresos', True, 1,
     'Ventas diarias de panificados'),
    ('Devoluciones y bonificaciones', 'ingreso', 'ingresos_netos', 'Descuentos', True, -1,
     'Notas de crédito, devoluciones, bonificaciones'),
    ('Compra MP/Insumos', 'egreso', 'cmv_stock', 'CMV', False, 1,
     'Compras que alimentan producción. En Brot Panel el CMV se calcula desde Costeo y Precios, no desde estas compras — se muestran solo a modo informativo.'),
    ('CMV directo', 'egreso', 'cmv', 'CMV', True, 1,
     'Solo si se decide registrar CMV directo (alternativo, normalmente sin uso).'),
    ('Mano de obra directa', 'egreso', 'mano_obra_directa', 'Producción', True, 1,
     'Sueldos productivos y cargas'),
    ('Packaging directo', 'egreso', 'gastos_variables', 'Packaging', True, 1,
     'Bolsas, etiquetas y embalaje asignable'),
    ('Logística y distribución', 'egreso', 'gastos_variables', 'Logística', True, 1,
     'Reparto, fletes, combustible directo'),
    ('Comisiones y medios de pago', 'egreso', 'gastos_variables', 'Comisiones', True, 1,
     'Mercado Pago, tarjetas y comisiones'),
    ('Energía eléctrica y gas', 'egreso', 'indirectos_productivos', 'Energía', True, 1,
     'Consumo productivo'),
    ('Mantenimiento productivo', 'egreso', 'indirectos_productivos', 'Mantenimiento', True, 1,
     'Repuestos, técnicos, abonos'),
    ('Alquiler / estructura planta', 'egreso', 'indirectos_productivos', 'Estructura', True, 1,
     'Alquiler y estructura productiva'),
    ('Limpieza e higiene', 'egreso', 'indirectos_productivos', 'Limpieza', True, 1,
     'Limpieza, higiene, bromatología'),
    ('Amortización económica activos', 'egreso', 'amortizaciones', 'Amortización', True, 1,
     'Se calcula automáticamente desde Costeo y Precios; no se asigna a compras.'),
    ('Administración y backoffice', 'egreso', 'gastos_administracion', 'Administración', True, 1,
     'Administrativos, gerencia, soporte'),
    ('Honorarios profesionales', 'egreso', 'gastos_administracion', 'Profesionales', True, 1,
     'Contador, asesorías, servicios profesionales'),
    ('Software y sistemas', 'egreso', 'gastos_administracion', 'Sistemas', True, 1,
     'Sistemas, licencias, servidor'),
    ('Impuestos y tasas', 'egreso', 'impuestos', 'Impuestos', True, 1,
     'IIBB, tasas, municipal, otros'),
    ('Débitos y créditos bancarios', 'egreso', 'gastos_financieros', 'Bancarios', True, 1,
     'Impuesto y gasto bancario'),
    ('Intereses y comisiones financieras', 'egreso', 'gastos_financieros', 'Financieros', True, 1,
     'Intereses, financiación, comisiones'),
    ('Otros ingresos', 'ingreso', 'otros_resultados', 'Otros ingresos', True, 1,
     'Ingresos no ordinarios'),
    ('Otros egresos', 'egreso', 'otros_resultados', 'Otros egresos', True, 1,
     'Egresos no clasificados'),
    ('Retiro dirección', 'egreso', 'no_eerr', 'Retiros', False, 1,
     'Retiros del dueño / socios. No impacta el EERR operativo.'),
    ('Compra activo / inversión', 'egreso', 'no_eerr', 'Inversión', False, 1,
     'Compra de maquinaria, vehículo o activo. No impacta el EERR operativo.'),
]


def seed_plan_cuentas(apps, schema_editor):
    PlanCuentaEERR = apps.get_model('gestion_gerencial', 'PlanCuentaEERR')
    for cuenta, tipo, linea_eerr, rubro, incluir_eerr, signo, descripcion in CUENTAS:
        PlanCuentaEERR.objects.get_or_create(
            cuenta=cuenta,
            defaults=dict(
                tipo=tipo,
                linea_eerr=linea_eerr,
                rubro=rubro,
                incluir_eerr=incluir_eerr,
                signo=signo,
                descripcion=descripcion,
            ),
        )


def eliminar_plan_cuentas(apps, schema_editor):
    PlanCuentaEERR = apps.get_model('gestion_gerencial', 'PlanCuentaEERR')
    nombres = [c[0] for c in CUENTAS]
    PlanCuentaEERR.objects.filter(cuenta__in=nombres).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('gestion_gerencial', '0007_plancuentaeerr_ventaproductoeerr_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_plan_cuentas, eliminar_plan_cuentas),
    ]