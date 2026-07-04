from django.db import models

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
    medida_1 = models.DecimalField(max_digits=6, decimal_places=1)
    medida_2 = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True)
    medida_3 = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True)
    familia = models.ForeignKey(Familia, on_delete=models.PROTECT)
    unidades_paquete = models.IntegerField()
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre

class TipoCliente(models.Model):
    nombre = models.CharField(max_length=50)

    def __str__(self):
        return self.nombre

class ListaPrecios(models.Model):
    nombre = models.CharField(max_length=50)
    tipo_cliente = models.ForeignKey(TipoCliente, on_delete=models.PROTECT)
    fecha = models.DateField()

    def __str__(self):
        return self.nombre

class Precio(models.Model):
    lista_precio = models.ForeignKey(ListaPrecios, on_delete=models.PROTECT)
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    precio = models.DecimalField(max_digits=6, decimal_places=2)

    def __str__(self):
        return f"{self.producto} - {str(self.precio)}"



