from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestion_gerencial', '0008_seed_plancuentaeerr'),
    ]

    operations = [
        migrations.AddField(
            model_name='snapshotcosteo',
            name='mes',
            field=models.CharField(blank=True, max_length=7, null=True, unique=True),
        ),
    ]