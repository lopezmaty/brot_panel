from django.db import migrations


# IDs obtenidos de obtener_precios_lista(20646) el 05/09/2026
# 32 matcheados por nombre exacto + 4 Burger Buns Chico mapeados manualmente
# (en Xubio se llaman "70 grs/Gr", en Costeo se llaman "Chico")
XUBIO_IDS = {
    'Bagels':                          1485486,
    'Burger Buns Clásico Chico':       3116855,
    'Burger Buns Clasico Grande':      3267121,
    'Burger Buns con Queso Chico':     3116859,
    'Burger Buns con Queso Grande':    3267122,
    'Burger Buns con Semillas Chico':  3116856,
    'Burger Buns con Semillas Grande': 3267123,
    'Burger Buns con Sesamo Chico':    3116858,
    'Burger Buns con Sesamo Grande':   3267124,
    'Pan de Campo Doble':              1485488,
    'Pan de Campo Simple':             1485490,
    'Pan de Lomo Campestre':           1485455,
    'Pan de Lomo Campestre Grande':    3105663,
    'Pan de Lomo Campestre Mini':      1485463,
    'Pan de Lomo Clasico':             1485453,
    'Pan de Lomo Clasico Grande':      1485456,
    'Pan de Lomo Clasico Mini':        1485461,
    'Pan de Lomo con Queso':           1511561,
    'Pan de Lomo con Queso Grande':    3250612,
    'Pan de Lomo con Queso Mini':      3160665,
    'Pan de Lomo con Semillas':        1485458,
    'Pan de Lomo con Semillas Grande': 3250615,
    'Pan de Lomo con Semillas Mini':   3217733,
    'Pan de Lomo Integral':            1485452,
    'Pan de Lomo Integral Grande':     3250613,
    'Pan de Lomo Integral Mini':       1485460,
    'Pan de Molde Blanco':             1485493,
    'Pan de Molde Blanco Campestre':   1485494,
    'Pan de Molde Campestre Grande':   1485495,
    'Pan de Molde Integral':           1485492,
    'Pan para Panchos':                3021008,
    'Pan para Pebetes':                1485487,
    'Tortuguita Campestre':            1485485,
    'Tortuguita Clasica':              1485483,
    'Tortuguita con Semillas':         1485484,
    'Tortuguita Integral':             1485481,
}


def poblar_xubio_ids(apps, schema_editor):
    ProductoCosteo = apps.get_model('gestion_gerencial', 'ProductoCosteo')
    actualizados = 0
    for nombre, xubio_id in XUBIO_IDS.items():
        updated = ProductoCosteo.objects.filter(nombre=nombre).update(xubio_producto_id=xubio_id)
        actualizados += updated
    print(f"xubio_producto_id poblado en {actualizados} productos.")


def limpiar_xubio_ids(apps, schema_editor):
    ProductoCosteo = apps.get_model('gestion_gerencial', 'ProductoCosteo')
    ProductoCosteo.objects.update(xubio_producto_id=None)


class Migration(migrations.Migration):

    dependencies = [
        ('gestion_gerencial', '0005_seed_costeo'),
    ]

    operations = [
        migrations.RunPython(poblar_xubio_ids, limpiar_xubio_ids),
    ]
