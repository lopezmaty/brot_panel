from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class Empleado(models.Model):
    """Legajo base de cada persona que trabaja en Brot Panes.

    No está atado a un usuario del panel: la mayoría de los empleados
    (panaderos, repartidores) no necesitan login. Si en algún momento
    alguno sí lo tiene, `usuario` lo vincula sin obligar a nadie más.
    """

    class Estado(models.TextChoices):
        ACTIVO = "activo", "Activo"
        INACTIVO = "inactivo", "Inactivo"

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="empleado",
    )
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    dni = models.CharField(max_length=15, unique=True)
    cuil = models.CharField(max_length=15, blank=True)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    domicilio = models.CharField(max_length=255, blank=True)
    telefono = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    foto = models.ImageField(upload_to="legajos/empleados/fotos/", null=True, blank=True)

    puesto = models.CharField(max_length=100)
    fecha_ingreso = models.DateField()
    fecha_baja = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.ACTIVO)

    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["apellido", "nombre"]

    def __str__(self):
        return f"{self.apellido}, {self.nombre}"

    @property
    def nombre_completo(self):
        return f"{self.nombre} {self.apellido}"

    @property
    def iniciales(self):
        return f"{self.nombre[:1]}{self.apellido[:1]}".upper()

    def proximo_cumpleanios(self, hoy=None):
        """Devuelve la fecha del próximo cumpleaños (este año o el que viene)."""
        if not self.fecha_nacimiento:
            return None
        hoy = hoy or timezone.localdate()
        try:
            cumple_este_anio = self.fecha_nacimiento.replace(year=hoy.year)
        except ValueError:
            # 29 de febrero en año no bisiesto
            cumple_este_anio = self.fecha_nacimiento.replace(year=hoy.year, day=28)
        if cumple_este_anio < hoy:
            try:
                cumple_este_anio = self.fecha_nacimiento.replace(year=hoy.year + 1)
            except ValueError:
                cumple_este_anio = self.fecha_nacimiento.replace(year=hoy.year + 1, day=28)
        return cumple_este_anio


class DocumentacionEmpleado(models.Model):
    """Documentos que el empleado ya trae hechos y solo se suben y controlan
    por vencimiento: carnet de manipulación de alimentos, credencial ART, etc.
    A diferencia de DocumentoPersonal, acá no se genera ni se firma nada.
    """

    class Tipo(models.TextChoices):
        CARNET_MANIPULACION = "carnet_manipulacion", "Carnet de manipulación de alimentos"
        CREDENCIAL_ART = "credencial_art", "Credencial ART"
        OTRO = "otro", "Otro"

    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name="documentacion")
    tipo = models.CharField(max_length=30, choices=Tipo.choices)
    tipo_otro_detalle = models.CharField(
        max_length=100, blank=True, help_text="Completar solo si el tipo es 'Otro'"
    )
    archivo = models.FileField(upload_to="legajos/documentacion/")
    fecha_emision = models.DateField(null=True, blank=True)
    fecha_vencimiento = models.DateField(null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["fecha_vencimiento"]

    def __str__(self):
        return f"{self.get_tipo_display()} — {self.empleado}"

    def estado_vencimiento(self, hoy=None):
        """'vigente' | 'por_vencer' (<=7 días) | 'vencido' | 'sin_vencimiento'"""
        if not self.fecha_vencimiento:
            return "sin_vencimiento"
        hoy = hoy or timezone.localdate()
        dias = (self.fecha_vencimiento - hoy).days
        if dias < 0:
            return "vencido"
        if dias <= 7:
            return "por_vencer"
        return "vigente"


class DocumentoPersonal(models.Model):
    """Patrón genérico para todo lo que se genera, se imprime, se firma en
    papel y se vuelve a subir escaneado: legajo inicial, apercibimientos,
    cambios de domicilio, comunicados, constancias, etc.
    """

    class Tipo(models.TextChoices):
        LEGAJO_INICIAL = "legajo_inicial", "Legajo inicial"
        APERCIBIMIENTO = "apercibimiento", "Apercibimiento"
        CAMBIO_DOMICILIO = "cambio_domicilio", "Cambio de domicilio"
        COMUNICADO = "comunicado", "Comunicado interno"
        CONSTANCIA_TRABAJO = "constancia_trabajo", "Constancia de trabajo"
        SUSPENSION = "suspension", "Suspensión"
        OTRO = "otro", "Otro"

    class Estado(models.TextChoices):
        BORRADOR = "borrador", "Borrador"
        GENERADO = "generado", "Generado, pendiente de firma"
        FIRMADO = "firmado", "Firmado"

    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name="documentos")
    tipo = models.CharField(max_length=30, choices=Tipo.choices)
    fecha = models.DateField(default=timezone.localdate)
    motivo = models.TextField(
        blank=True, help_text="Detalle que completa el admin; se usa para armar el texto a imprimir"
    )
    domicilio_nuevo = models.CharField(
        max_length=255, blank=True, help_text="Solo para tipo 'Cambio de domicilio'"
    )

    pdf_generado = models.FileField(upload_to="legajos/documentos/generados/", null=True, blank=True)
    archivo_firmado = models.FileField(upload_to="legajos/documentos/firmados/", null=True, blank=True)

    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.BORRADOR)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    firmado_en = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.get_tipo_display()} — {self.empleado} ({self.fecha})"

    def save(self, *args, **kwargs):
        # Si se acaba de subir el firmado y todavía no tiene fecha de firma, la completamos.
        if self.archivo_firmado and not self.firmado_en:
            self.firmado_en = timezone.localdate()
            self.estado = self.Estado.FIRMADO
        super().save(*args, **kwargs)

        # Cambio de domicilio firmado: actualiza el domicilio actual del empleado.
        if self.tipo == self.Tipo.CAMBIO_DOMICILIO and self.estado == self.Estado.FIRMADO and self.domicilio_nuevo:
            if self.empleado.domicilio != self.domicilio_nuevo:
                self.empleado.domicilio = self.domicilio_nuevo
                self.empleado.save(update_fields=["domicilio"])


class Ausencia(models.Model):
    class Tipo(models.TextChoices):
        ENFERMEDAD = "enfermedad", "Enfermedad"
        PERSONAL = "personal", "Personal"
        INJUSTIFICADA = "injustificada", "Injustificada"
        VACACIONES = "vacaciones", "Vacaciones"
        ART = "art", "Accidente / ART"
        OTRA = "otra", "Otra"

    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name="ausencias")
    fecha_desde = models.DateField()
    fecha_hasta = models.DateField()
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    justificada = models.BooleanField(default=False)
    certificado = models.FileField(upload_to="legajos/ausencias/", null=True, blank=True)
    observaciones = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha_desde"]

    def __str__(self):
        return f"{self.empleado} — {self.get_tipo_display()} ({self.fecha_desde} a {self.fecha_hasta})"


class Novedad(models.Model):
    class Tipo(models.TextChoices):
        AVISO = "aviso", "Aviso"
        CAMBIO = "cambio", "Cambio"
        FELICITACION = "felicitacion", "Felicitación"
        OTRA = "otra", "Otra"

    empleado = models.ForeignKey(
        Empleado,
        on_delete=models.CASCADE,
        related_name="novedades",
        null=True,
        blank=True,
        help_text="Vacío = novedad general para todo el equipo",
    )
    fecha = models.DateField(default=timezone.localdate)
    tipo = models.CharField(max_length=20, choices=Tipo.choices, default=Tipo.AVISO)
    texto = models.TextField()
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha", "-creado_en"]

    def __str__(self):
        destinatario = self.empleado or "General"
        return f"{self.fecha} — {destinatario}: {self.texto[:40]}"


class AvisoEnviado(models.Model):
    """Registro de qué avisos por mail ya se mandaron, para no duplicarlos
    si el chequeo diario corre más de una vez.
    """

    class Tipo(models.TextChoices):
        DOCUMENTACION_VENCIMIENTO = "documentacion_vencimiento", "Vencimiento de documentación"
        CUMPLEANIOS = "cumpleanios", "Cumpleaños"

    tipo = models.CharField(max_length=30, choices=Tipo.choices)
    referencia_id = models.PositiveIntegerField(help_text="ID de DocumentacionEmpleado o Empleado")
    fecha_aviso = models.DateField(help_text="Fecha 'lógica' del aviso: hoy o 7 días antes")
    enviado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("tipo", "referencia_id", "fecha_aviso")

    def __str__(self):
        return f"{self.tipo} #{self.referencia_id} — {self.fecha_aviso}"