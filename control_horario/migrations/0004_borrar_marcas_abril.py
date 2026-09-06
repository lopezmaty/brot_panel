from django.db import migrations


def borrar_abril(apps, schema_editor):
    MarcaFichada = apps.get_model('control_horario', 'MarcaFichada')
    borradas, _ = MarcaFichada.objects.filter(mes='2026-04').delete()
    print(f'Marcas de abril borradas: {borradas}')


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('control_horario', '0003_rename_control_hor_mes_marcas_idx_control_hor_mes_6e58ef_idx_and_more'),
    ]

    operations = [
        migrations.RunPython(borrar_abril, noop),
    ]