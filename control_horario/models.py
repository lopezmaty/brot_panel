from django.conf import settings
from django.db import models


class Empleado(models.Model):
    nombre = models.CharField(max_length=200, unique=True)

    # Nombre completo que se muestra
    alias = models.CharField(max_length=200, blank=True, default='')

    # Nombre EXACTO recibido desde el reloj
    nombre_reloj = models.CharField(
        max_length=200,
        blank=True,
        default='',
        db_index=True
    )

    # Legajo del empleado (módulo Legajos): de ahí salen DNI, puesto y nombre completo
    legajo = models.OneToOneField(
        'legajos.Empleado', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='empleado_reloj',
    )

    # Datos que pide el Anexo I (se usan si el empleado no tiene legajo vinculado)
    dni = models.CharField(max_length=15, blank=True, default='')
    sector_turno = models.CharField(max_length=100, blank=True, default='')

    medio_jornada = models.BooleanField(default=False)
    sin_descuento_descanso = models.BooleanField(default=False)
    bono_horas_extra = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

    def nombre_display(self):
        return self.nombre


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

class ConfigHorario(models.Model):
    """Parámetros del módulo (una sola fila)."""
    limite_incidencias_mes = models.PositiveIntegerField(
        default=3,
        help_text='Cantidad de rectificaciones en un mes a partir de la cual se sugiere evaluar un apercibimiento.',
    )

    @classmethod
    def actual(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class RectificacionFichada(models.Model):
    """Reporte y corrección excepcional de fichada (Anexo I del Reglamento).

    Nunca modifica las marcas del reloj: queda registrada aparte y, si se
    autoriza, reemplaza sólo las horas a liquidar de ese día.
    """

    class Estado(models.TextChoices):
        PENDIENTE_FIRMA = 'pendiente_firma', 'Pendiente de firma y foto'
        PENDIENTE_RESOLUCION = 'pendiente_resolucion', 'Pendiente de resolución'
        RESUELTA = 'resuelta', 'Resuelta'
        ANULADA = 'anulada', 'Anulada'

    class Resolucion(models.TextChoices):
        ACREDITADA = 'acreditada', 'Incidencia acreditada: se autoriza corrección excepcional'
        PARCIAL = 'parcial', 'Incidencia parcialmente acreditada: se autoriza corrección por el horario comprobado'
        NO_ACREDITADA = 'no_acreditada', 'Incidencia no acreditada: se mantiene el cálculo administrativo provisional'

    TIPOS = [
        ('ingreso', 'Entrada'),
        ('salida', 'Salida'),
        ('descanso', 'Descanso'),
        ('falla_tecnica', 'Falla técnica'),
        ('otro', 'Otro'),
    ]
    CAMARAS = [('si', 'Sí'), ('no', 'No'), ('no_disponibles', 'No disponibles')]

    empleado = models.ForeignKey(Empleado, on_delete=models.PROTECT, related_name='rectificaciones')
    fecha = models.DateField(help_text='Fecha de la incidencia')
    estado = models.CharField(max_length=25, choices=Estado.choices, default=Estado.PENDIENTE_FIRMA)

    # ── Parte 1: declaración de la persona trabajadora ──
    dni = models.CharField(max_length=15, blank=True, default='')
    sector_turno = models.CharField(max_length=100, blank=True, default='')
    tipos = models.JSONField(default=list, help_text='Lista de tipos de incidencia')
    tipo_otro = models.CharField(max_length=120, blank=True, default='')
    marcas_originales = models.CharField(max_length=300, blank=True, default='', help_text='Copia de las marcas del reloj al momento del pedido')
    calculo_provisional = models.CharField(max_length=300, blank=True, default='')
    horas_provisionales = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    real_entrada = models.TimeField(null=True, blank=True)
    real_salida_descanso = models.TimeField(null=True, blank=True)
    real_regreso_descanso = models.TimeField(null=True, blank=True)
    real_salida = models.TimeField(null=True, blank=True)
    sin_descanso_declarado = models.BooleanField(default=False, help_text='El trabajador declara que no pudo tomar el descanso')
    horario_real_texto = models.CharField(max_length=300, blank=True, default='')
    motivo = models.TextField()
    fecha_hora_aviso = models.DateTimeField()
    medio_aviso = models.CharField(max_length=200, blank=True, default='Formulario entregado al responsable designado.')
    creada_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    creada_el = models.DateTimeField(auto_now_add=True)

    # ── Formulario firmado ──
    foto = models.FileField(upload_to='control_horario/rectificaciones/', null=True, blank=True)
    foto_subida_el = models.DateTimeField(null=True, blank=True)
    foto_subida_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')

    # ── Parte 2: verificación interna y resolución ──
    verif_biometrico = models.BooleanField(null=True, blank=True)
    verif_horario_programado = models.BooleanField(null=True, blank=True)
    verif_camaras = models.CharField(max_length=15, choices=CAMARAS, blank=True, default='')
    verif_registros = models.BooleanField(null=True, blank=True)
    verif_supervisor = models.BooleanField(null=True, blank=True)
    verif_otros = models.TextField(blank=True, default='')
    resolucion = models.CharField(max_length=15, choices=Resolucion.choices, blank=True, default='')
    horario_corregido = models.CharField(max_length=200, blank=True, default='')
    horas_a_liquidar = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    observaciones = models.TextField(blank=True, default='')
    aprobado_por = models.CharField(max_length=150, blank=True, default='', help_text='Responsable que firmó la resolución en papel')
    resuelta_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    resuelta_el = models.DateTimeField(null=True, blank=True)

    # ── Anulación (no se borra: queda registrada) ──
    motivo_anulacion = models.CharField(max_length=300, blank=True, default='')
    anulada_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    anulada_el = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-fecha', '-id']
        indexes = [models.Index(fields=['empleado', 'fecha'])]

    def __str__(self):
        return f'Rectificación #{self.numero} — {self.empleado.nombre} {self.fecha:%d/%m/%Y}'

    @property
    def numero(self):
        return f'{self.id:05d}' if self.id else '—'

    @property
    def autoriza_correccion(self):
        return (
            self.estado == self.Estado.RESUELTA
            and self.resolucion in (self.Resolucion.ACREDITADA, self.Resolucion.PARCIAL)
            and self.horas_a_liquidar is not None
        )

    @property
    def aviso_fuera_de_termino(self):
        """Reglamento §7: el aviso debe darse dentro de las 48 h de ocurrida la incidencia."""
        if not self.fecha_hora_aviso:
            return False
        from datetime import datetime, time, timedelta
        from django.utils import timezone as dj_tz
        fin_del_dia = dj_tz.make_aware(datetime.combine(self.fecha, time(23, 59, 59)))
        return self.fecha_hora_aviso > fin_del_dia + timedelta(hours=48)