from django.db import models


class Empleado(models.Model):
    nombre = models.CharField(max_length=200, unique=True)
    alias = models.CharField(max_length=200, blank=True, default='')
    medio_jornada = models.BooleanField(default=False)
    sin_descuento_descanso = models.BooleanField(default=False)
    bono_horas_extra = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['nombre']

    def __str__(self):
        return self.alias or self.nombre

    def nombre_display(self):
        return self.alias or self.nombre


class MarcaFichada(models.Model):
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name='marcas')
    timestamp = models.DateTimeField()
    mes = models.CharField(max_length=7)  # 'YYYY-MM'

    class Meta:
        unique_together = ('empleado', 'timestamp')
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['mes']),
            models.Index(fields=['empleado', 'mes']),
        ]

    def __str__(self):
        return f'{self.empleado.nombre} @ {self.timestamp:%Y-%m-%d %H:%M:%S}'


class AjusteMes(models.Model):
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name='ajustes')
    mes = models.CharField(max_length=7)
    faltas = models.JSONField(default=list, blank=True)
    feriados = models.JSONField(default=list, blank=True)
    vacaciones = models.JSONField(default=dict, blank=True)
    observacion = models.TextField(blank=True, default='')

    class Meta:
        unique_together = ('empleado', 'mes')

    def __str__(self):
        return f'{self.empleado.nombre} — {self.mes}'


class ErrorFichadaManual(models.Model):
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name='errores_manuales')
    fecha = models.DateField()

    class Meta:
        unique_together = ('empleado', 'fecha')

    def __str__(self):
        return f'{self.empleado.nombre} — {self.fecha}'


class HistorialMes(models.Model):
    mes = models.CharField(max_length=7, unique=True)
    cerrado_el = models.DateTimeField(auto_now_add=True)
    cerrado_por = models.CharField(max_length=200, blank=True, default='')
    snapshot = models.JSONField()

    class Meta:
        ordering = ['-mes']

    def __str__(self):
        return f'Cierre {self.mes}'


class LiquidacionHoras(models.Model):
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name='liquidaciones')
    fecha = models.DateField()
    monto = models.DecimalField(max_digits=8, decimal_places=2)
    comentario = models.TextField(blank=True, default='')
    registrado_el = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha']

    def __str__(self):
        return f'{self.empleado.nombre} — {self.fecha} — {self.monto}h'