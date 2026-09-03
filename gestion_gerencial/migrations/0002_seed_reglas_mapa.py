from django.db import migrations

REGLAS = [
    ('MOLINO CAÑUELAS SOCIEDAD ANONIMA COMERCIAL INDUSTRIAL  FINANCIERA INMOBILIARIA Y AGROPECUARIA', '*', 'materia_prima'),
    ('PRINCOR SRL', '*', 'materia_prima'),
    ('PANHEL S R L', '*', 'materia_prima'),
    ('SERGIO BARBERO S.A.S.', '*', 'materia_prima'),
    ('MESAL S.A.S.', '*', 'materia_prima'),
    ('BYC', '*', 'materia_prima'),
    ('LA QUESERIA', '*', 'materia_prima'),
    ('BOLSAS EDGARDO', '*', 'materia_prima'),
    ('ALMACEN', 'LECHE', 'materia_prima'),
    ('ALMACEN', 'ARTICULOS LIMPIEZA', 'gastos_fijos'),
    ('ALMACEN', 'GASTOS INSUMOS', 'gastos_fijos'),
    ('GASTOS INSUMOS', 'ALCOHOL', 'gastos_fijos'),
    ('GASTOS INSUMOS', 'LECHE', 'materia_prima'),
    ('GASTOS INSUMOS', 'GASTOS VARIOS', 'gastos_fijos'),
    ('DISTRIBUIDORA ESTRELLA AZUL SRL', '*', 'gastos_fijos'),
    ('ALQUILER', '*', 'gastos_fijos'),
    ('EPEC', '*', 'gastos_fijos'),
    ('ECOGAS', '*', 'gastos_fijos'),
    ('BRUNETTI HERMANOS S.R.L.', '*', 'gastos_fijos'),
    ('BERNARDITA RUTH SOBA', '*', 'gastos_fijos'),
    ('CLARO INTERNET', '*', 'gastos_fijos'),
    ('LIMPIEZA  RINCÓN', '*', 'gastos_fijos'),
    ('FERRETERÍA', '*', 'gastos_fijos'),
    ('SUELDOS', '*', 'sueldos_productivos'),
    ('SUELDOS', 'SUELDO DIRECTOR', 'honorarios_direccion'),
    ('TANIA MELINA ARRIAGA', '*', 'administracion'),
    ('LUCIA COMMERES BENEJAM', '*', 'administracion'),
    ('XUBIO', '*', 'administracion'),
    ('LIBRERÍA', '*', 'administracion'),
    ('EDENRED ARGENTINA SOCIEDAD ANONIMA', '*', 'logistica'),
    ('LOGISTICA', '*', 'logistica'),
    ('IMPUESTOS', '*', 'impuestos'),
    ('MATIAS EMANUEL LOPEZ', 'RETIRO SOCIETARIO', 'retiro_societario'),
    ('INVERSIONES', '*', 'capex'),
    ('MONTEQUIN SA', '*', 'capex'),
]


def seed_reglas(apps, schema_editor):
    ReglaCategorizacionMapa = apps.get_model('gestion_gerencial', 'ReglaCategorizacionMapa')
    for proveedor, producto, rubro in REGLAS:
        ReglaCategorizacionMapa.objects.get_or_create(
            proveedor=proveedor, producto=producto, defaults={'rubro': rubro}
        )


def eliminar_reglas(apps, schema_editor):
    ReglaCategorizacionMapa = apps.get_model('gestion_gerencial', 'ReglaCategorizacionMapa')
    ReglaCategorizacionMapa.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('gestion_gerencial', '0001_initial'),  # ajustá este nombre al de tu primera migración real
    ]

    operations = [
        migrations.RunPython(seed_reglas, eliminar_reglas),
    ]