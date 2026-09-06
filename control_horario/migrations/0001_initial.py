from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Empleado',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=200, unique=True)),
                ('alias', models.CharField(blank=True, default='', max_length=200)),
                ('medio_jornada', models.BooleanField(default=False)),
                ('sin_descuento_descanso', models.BooleanField(default=False)),
                ('bono_horas_extra', models.DecimalField(decimal_places=2, default=0, max_digits=6)),
                ('activo', models.BooleanField(default=True)),
            ],
            options={'ordering': ['nombre']},
        ),
        migrations.CreateModel(
            name='MarcaFichada',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField()),
                ('mes', models.CharField(max_length=7)),
                ('empleado', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='marcas', to='control_horario.empleado')),
            ],
            options={'ordering': ['timestamp']},
        ),
        migrations.AddIndex(
            model_name='marcafichada',
            index=models.Index(fields=['mes'], name='control_hor_mes_marcas_idx'),
        ),
        migrations.AddIndex(
            model_name='marcafichada',
            index=models.Index(fields=['empleado', 'mes'], name='control_hor_emp_mes_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='marcafichada',
            unique_together={('empleado', 'timestamp')},
        ),
        migrations.CreateModel(
            name='AjusteMes',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mes', models.CharField(max_length=7)),
                ('faltas', models.JSONField(blank=True, default=list)),
                ('feriados', models.JSONField(blank=True, default=list)),
                ('vacaciones', models.JSONField(blank=True, default=dict)),
                ('observacion', models.TextField(blank=True, default='')),
                ('empleado', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ajustes', to='control_horario.empleado')),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='ajustemes',
            unique_together={('empleado', 'mes')},
        ),
        migrations.CreateModel(
            name='ErrorFichadaManual',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha', models.DateField()),
                ('empleado', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='errores_manuales', to='control_horario.empleado')),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='errorfichadamanual',
            unique_together={('empleado', 'fecha')},
        ),
        migrations.CreateModel(
            name='HistorialMes',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mes', models.CharField(max_length=7, unique=True)),
                ('cerrado_el', models.DateTimeField(auto_now_add=True)),
                ('cerrado_por', models.CharField(blank=True, default='', max_length=200)),
                ('snapshot', models.JSONField()),
            ],
            options={'ordering': ['-mes']},
        ),
        migrations.CreateModel(
            name='LiquidacionHoras',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha', models.DateField()),
                ('monto', models.DecimalField(decimal_places=2, max_digits=8)),
                ('comentario', models.TextField(blank=True, default='')),
                ('registrado_el', models.DateTimeField(auto_now_add=True)),
                ('empleado', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='liquidaciones', to='control_horario.empleado')),
            ],
            options={'ordering': ['-fecha']},
        ),
    ]