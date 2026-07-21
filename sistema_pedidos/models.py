from django.db import models
from lista_precios.models import TipoCliente, Producto

# Create your models here.

class Cliente(models.Model):

    COND_IVA = [
        ('responsable_inscripto', 'Responsable Inscripto'),
        ('monotributista', 'Monotributista'),
        ('consumidor_final', 'Consumidor Final')
    ]

    nombre = models.CharField(max_length=50)
    razon_social = models.CharField(max_length=50)
    cuit = models.CharField(max_length=13)
    nombre_comercio = models.CharField(max_length=50)
    direccion = models.CharField(max_length=150)
    ciudad = models.CharField(max_length=50)
    provincia = models.CharField(max_length=50)
    telefono = models.CharField(max_length=15)
    mail = models.EmailField()
    condicion_iva = models.CharField(max_length=50, choices=COND_IVA)
    tipo_cliente = models.ForeignKey(TipoCliente, on_delete=models.PROTECT)
    activo = models.BooleanField(default=True)
    token = models.CharField(max_length=100, null=True, blank=True)
    token_expiracion = models.DateTimeField(null=True, blank=True)
    posee_deuda = models.BooleanField(default=False)

    def __str__(self):
        return self.nombre


class Pedido(models.Model):
    ESTADO_PEDIDO = [
        ('nuevo', 'Nuevo'),
        ('en_proceso', 'En Proceso'),
        ('completado', 'Completado'),
        ('cancelado', 'Cancelado')
    ]

    ENTREGA = [
        ('retiro', 'Retiro en Fabrica'),
        ('entrega_domicilio', 'Entrega en Domicilio')
    ]

    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT)
    fecha = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=50, choices=ESTADO_PEDIDO, default='nuevo')
    metodo_entrega = models.CharField(max_length=50, choices=ENTREGA)

    def __str__(self):
        return f"Pedido #{str(self.id).zfill(4)}"
    

class ItemPedido(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.IntegerField()
    precio = models.DecimalField(max_digits=4, decimal_places=2)
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.producto)