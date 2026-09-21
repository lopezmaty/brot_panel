from django.conf import settings
from django.db import models
from django.db.models import Q

# Create your models here.

class Variedad(models.Model):
    nombre = models.CharField(max_length=50)

    def __str__(self):
        return self.nombre

class Tamaño(models.Model):
    nombre = models.CharField(max_length=50)

    def __str__(self):
        return self.nombre

class Familia(models.Model):
    nombre = models.CharField(max_length=50)

    def __str__(self):
        return self.nombre

class Producto(models.Model):

    TIPO_MEDIDA = [
    ('diametro', 'Diámetro'),
    ('largo_ancho', 'Largo x Ancho'),
    ('largo_ancho_alto', 'Largo x Ancho x Alto'),
]
    nombre = models.CharField(max_length=50)
    variedad = models.ForeignKey(Variedad, on_delete=models.PROTECT)
    tamaño = models.ForeignKey(Tamaño, on_delete=models.PROTECT)
    tipo_medida = models.CharField(max_length=20, choices=TIPO_MEDIDA)
    medida_1 = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True)
    medida_2 = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True)
    medida_3 = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True)
    familia = models.ForeignKey(Familia, on_delete=models.PROTECT)
    unidades_paquete = models.IntegerField()
    activo = models.BooleanField(default=True)

    xubio_producto_id = models.IntegerField(null=True, blank=True)

    clientes_exclusivos = models.ManyToManyField(
    'sistema_pedidos.Cliente',
    blank=True,
    related_name='productos_exclusivos')

    def __str__(self):
        return f'{self.nombre} {self.variedad} {self.tamaño}'

class TipoCliente(models.Model):
    nombre = models.CharField(max_length=50)

    def __str__(self):
        return self.nombre

class ListaPrecios(models.Model):
    nombre = models.CharField(max_length=50)
    fecha = models.DateField()
    pdf_catalogo = models.FileField(upload_to='catalogos/', null=True, blank=True)
    xubio_lista_precio_id = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return self.nombre

class Precio(models.Model):
    lista_precio = models.ForeignKey(ListaPrecios, on_delete=models.PROTECT)
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    precio = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.producto} - {str(self.precio)}"

class HistorialPrecio(models.Model):
    lista_precio = models.ForeignKey(ListaPrecios, on_delete=models.CASCADE, related_name='historial')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='historial_precios')
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.producto} - {self.precio} ({self.fecha:%d/%m/%Y})"


class ActualizacionPrecios(models.Model):
    ESTADOS = [
        ('programada', 'Programada'),
        ('aplicada', 'Aplicada'),
        ('cancelada', 'Cancelada'),
    ]

    lista_precio = models.ForeignKey(
        ListaPrecios, on_delete=models.CASCADE, related_name='actualizaciones'
    )
    vigente_desde = models.DateTimeField()
    estado = models.CharField(max_length=20, choices=ESTADOS, default='programada')
    creada = models.DateTimeField(auto_now_add=True)
    creada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    aplicada_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-vigente_desde']
        constraints = [
            models.UniqueConstraint(
                fields=['lista_precio'],
                condition=Q(estado='programada'),
                name='una_programada_por_lista',
            )
        ]

    def __str__(self):
        return f"{self.lista_precio} desde {self.vigente_desde:%d/%m/%Y} ({self.estado})"


class ItemActualizacionPrecios(models.Model):
    actualizacion = models.ForeignKey(
        ActualizacionPrecios, on_delete=models.CASCADE, related_name='items'
    )
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    precio_anterior = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    precio_nuevo = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ('actualizacion', 'producto')

    def __str__(self):
        return f"{self.producto}: {self.precio_anterior} → {self.precio_nuevo}"