from django.db import models

# Configuración de rubros del Mapa Económico — igual a la del HTML original,
# no es editable desde el panel (a propósito, para no romper los objetivos definidos).
RUBROS_MAPA = [
    {'id': 'materia_prima', 'nombre': 'Materia prima e insumos directos', 'objetivo': 0.33, 'verde_min': 0.28, 'verde_max': 0.38, 'amar_max': 0.41},
    {'id': 'sueldos_productivos', 'nombre': 'Sueldos productivos (incl. administrativos)', 'objetivo': 0.23, 'verde_min': 0.18, 'verde_max': 0.28, 'amar_max': 0.31},
    {'id': 'administracion', 'nombre': 'Administración', 'objetivo': 0.04, 'verde_min': 0.04, 'verde_max': 0.07, 'amar_max': 0.09},
    {'id': 'honorarios_direccion', 'nombre': 'Honorarios dirección', 'objetivo': 0.03, 'verde_min': 0.03, 'verde_max': 0.06, 'amar_max': 0.09},
    {'id': 'gastos_fijos', 'nombre': 'Gastos fijos operativos', 'objetivo': 0.14, 'verde_min': 0.10, 'verde_max': 0.18, 'amar_max': 0.21},
    {'id': 'logistica', 'nombre': 'Logística y distribución', 'objetivo': 0.08, 'verde_min': 0.05, 'verde_max': 0.12, 'amar_max': 0.14},
    {'id': 'impuestos', 'nombre': 'Impuestos', 'objetivo': 0.04, 'verde_min': 0.03, 'verde_max': 0.07, 'amar_max': 0.08},
    {'id': 'financieros', 'nombre': 'Financieros', 'objetivo': 0.02, 'verde_min': 0.01, 'verde_max': 0.03, 'amar_max': 0.04},
]

FUERA_OPERATIVA_MAPA = [
    {'id': 'capex', 'nombre': 'Capex / Inversiones'},
    {'id': 'retiro_societario', 'nombre': 'Retiro societario / distribución de utilidades'},
    {'id': 'otro_excluir', 'nombre': 'Otro / gasto personal (excluir)'},
]

SIN_CATEGORIZAR = 'sin_categorizar'

RUBRO_CHOICES = (
    [(r['id'], r['nombre']) for r in RUBROS_MAPA]
    + [(r['id'], r['nombre']) for r in FUERA_OPERATIVA_MAPA]
    + [(SIN_CATEGORIZAR, 'Sin categorizar')]
)


class ReglaCategorizacionMapa(models.Model):
    """Aprendizaje: proveedor+producto -> rubro. producto='*' significa 'cualquier producto de ese proveedor'."""
    proveedor = models.CharField(max_length=200)
    producto = models.CharField(max_length=200, blank=True, default='*')
    rubro = models.CharField(max_length=30, choices=RUBRO_CHOICES)

    class Meta:
        unique_together = ('proveedor', 'producto')

    def __str__(self):
        return f'{self.proveedor} / {self.producto} → {self.rubro}'


class CompraMapa(models.Model):
    mes = models.CharField(max_length=7)  # 'YYYY-MM'
    fecha = models.DateField(null=True, blank=True)
    documento = models.CharField(max_length=50, blank=True, default='')
    proveedor = models.CharField(max_length=200)
    producto = models.CharField(max_length=200, blank=True, default='')
    descripcion = models.CharField(max_length=300, blank=True, default='')
    importe = models.DecimalField(max_digits=12, decimal_places=2)
    rubro = models.CharField(max_length=30, choices=RUBRO_CHOICES, default=SIN_CATEGORIZAR)
    xubio_transaccion_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=['mes'])]

    def __str__(self):
        return f'{self.proveedor} - {self.importe} ({self.mes})'


class DatosMesMapa(models.Model):
    mes = models.CharField(max_length=7, unique=True)
    ventas_netas = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    unidades = models.IntegerField(default=0)
    clientes_activos = models.IntegerField(default=0)
    clientes_80 = models.IntegerField(default=0)
    productos_80 = models.IntegerField(default=0)
    observaciones = models.CharField(max_length=500, blank=True, default='')

    def __str__(self):
        return self.mes


class VentaClienteMapa(models.Model):
    mes = models.CharField(max_length=7)
    cliente = models.CharField(max_length=200)
    importe = models.DecimalField(max_digits=12, decimal_places=2)
    cantidad = models.IntegerField(default=0)

    class Meta:
        indexes = [models.Index(fields=['mes'])]


class VentaProductoMapa(models.Model):
    mes = models.CharField(max_length=7)
    producto = models.CharField(max_length=200)
    importe = models.DecimalField(max_digits=12, decimal_places=2)
    cantidad = models.IntegerField(default=0)

    class Meta:
        indexes = [models.Index(fields=['mes'])]

class CompraMapa(models.Model):
    mes = models.CharField(max_length=7)  # 'YYYY-MM'
    fecha = models.DateField(null=True, blank=True)
    documento = models.CharField(max_length=50, blank=True, default='')
    proveedor = models.CharField(max_length=200)
    producto = models.CharField(max_length=200, blank=True, default='')
    descripcion = models.CharField(max_length=300, blank=True, default='')
    importe = models.DecimalField(max_digits=12, decimal_places=2)
    rubro = models.CharField(max_length=30, choices=RUBRO_CHOICES, default=SIN_CATEGORIZAR)
    xubio_transaccion_id = models.BigIntegerField(null=True, blank=True)
    xubio_item_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=['mes'])]

    def __str__(self):
        return f'{self.proveedor} - {self.importe} ({self.mes})'

# Create your models here.
