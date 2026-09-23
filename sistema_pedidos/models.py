from django.conf import settings
from django.db import models
from lista_precios.models import TipoCliente, Producto, ListaPrecios, ActualizacionPrecios

# Create your models here.

class Cliente(models.Model):

    COND_IVA = [
        ('responsable_inscripto', 'Responsable Inscripto'),
        ('monotributista', 'Monotributista'),
        ('consumidor_final', 'Consumidor Final')
    ]

    TIPO_COMPROBANTE = [
        (1, 'Factura'),
        (6, 'Recibo'),
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
    lista_precios = models.ForeignKey(ListaPrecios, on_delete=models.PROTECT, null=True, blank=True)

    # Campos Xubio
    xubio_cliente_id = models.IntegerField(null=True, blank=True)
    xubio_punto_venta_id = models.IntegerField(null=True, blank=True)
    xubio_tipo_comprobante = models.IntegerField(choices=TIPO_COMPROBANTE, null=True, blank=True)
    dias_cc = models.IntegerField(default=0)

    permite_retiro = models.BooleanField(default=True)
    permite_domicilio = models.BooleanField(default=True)

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
    observaciones = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return f"Pedido #{str(self.id).zfill(4)}"
    

class ItemPedido(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.IntegerField()
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.producto)

class StockProducto(models.Model):
    xubio_producto_id = models.IntegerField(unique=True)
    nombre = models.CharField(max_length=100)
    stock_actual = models.IntegerField(default=0)
    actualizado = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nombre


class Comunicacion(models.Model):
    """Una comunicación enviada a clientes: el aviso de una lista de precios
    nueva, o una comunicación general (botón "Comunicación a clientes")."""

    ORIGENES = [
        ('lista_precios', 'Nueva lista de precios'),
        ('manual', 'Comunicación general'),
    ]

    titulo = models.CharField(max_length=120)
    mensaje = models.TextField()
    origen = models.CharField(max_length=20, choices=ORIGENES)
    actualizacion = models.ForeignKey(
        ActualizacionPrecios, on_delete=models.CASCADE,
        null=True, blank=True, related_name='comunicaciones',
    )
    creada = models.DateTimeField(auto_now_add=True)
    creada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        ordering = ['-creada']

    def __str__(self):
        return f'{self.titulo} ({self.creada:%d/%m/%Y})'


class ComunicacionDestinatario(models.Model):
    """Un cliente notificado de una Comunicacion: si la leyó y si se le mandó el mail."""

    comunicacion = models.ForeignKey(
        Comunicacion, on_delete=models.CASCADE, related_name='destinatarios'
    )
    cliente = models.ForeignKey(
        Cliente, on_delete=models.CASCADE, related_name='comunicaciones'
    )
    leida_en = models.DateTimeField(null=True, blank=True)
    mail_enviado = models.BooleanField(default=False)

    class Meta:
        unique_together = ('comunicacion', 'cliente')

    def __str__(self):
        return f'{self.comunicacion} -> {self.cliente}'