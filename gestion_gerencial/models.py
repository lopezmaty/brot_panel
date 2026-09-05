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

IVA_RATE_COSTEO = 0.105

XUBIO_LISTA_GASTRONOMICO_ID = 20646
XUBIO_LISTA_DISTRIBUIDOR_ID = 20357


class ProductoCosteo(models.Model):
    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=150)
    familia = models.CharField(max_length=100)
    peso = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    precio_actual = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # gastronómico sin IVA
    precio_con_iva = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # gastronómico con IVA
    precio_distribuidor = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    unidades_mes = models.IntegerField(default=0)
    unidades_lote = models.IntegerField(default=0)
    margen_objetivo = models.DecimalField(max_digits=7, decimal_places=6, null=True, blank=True)
    descuento_objetivo = models.DecimalField(max_digits=7, decimal_places=6, null=True, blank=True)
    xubio_producto_id = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ['nombre']

    def __str__(self):
        return f'{self.codigo} - {self.nombre}'


class InsumoCosteo(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    unidad = models.CharField(max_length=20)
    precio = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    comentario = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class RecetaLineaCosteo(models.Model):
    producto = models.ForeignKey(ProductoCosteo, on_delete=models.CASCADE, related_name='receta')
    insumo = models.ForeignKey(InsumoCosteo, on_delete=models.PROTECT)
    categoria = models.CharField(max_length=50, blank=True, default='')
    unidad = models.CharField(max_length=20, blank=True, default='')
    cantidad = models.DecimalField(max_digits=12, decimal_places=6, default=0)
    merma = models.DecimalField(max_digits=5, decimal_places=4, default=0)

    def __str__(self):
        return f'{self.producto.codigo} - {self.insumo.nombre}'


class ManoObraCosteo(models.Model):
    producto = models.OneToOneField(ProductoCosteo, on_delete=models.CASCADE, related_name='mano_obra')
    proceso = models.CharField(max_length=200, blank=True, default='')
    personas = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    tiempo_min_lote = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    def __str__(self):
        return f'{self.producto.codigo} - mano de obra'


class ConfiguracionCosteo(models.Model):
    """Singleton — una sola fila para toda la app (id=1)."""
    sueldos_productivos = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    horas_disponibles = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    margen_minimo = models.DecimalField(max_digits=6, decimal_places=4, default=0.10)
    energia = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    mantenimiento = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    limpieza = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sueldos_indirectos = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    resto = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    aguinaldos = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    alquiler = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    muni = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    iva = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    ganancias = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    contador = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return 'Configuración de Costeo'


class EquipoCosteo(models.Model):
    nombre = models.CharField(max_length=100)
    valor_reposicion = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    vida_util_anios = models.IntegerField(default=1)

    def __str__(self):
        return self.nombre


class HistorialPrecioCosteo(models.Model):
    fecha = models.DateTimeField(auto_now_add=True)
    tipo = models.CharField(max_length=50)  # 'gastronomico' | 'distribuidor' | 'insumo' etc.
    item = models.CharField(max_length=200)
    valor_anterior = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    valor_nuevo = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        ordering = ['-fecha']

    def __str__(self):
        return f'{self.item}: {self.valor_anterior} → {self.valor_nuevo}'


class SnapshotCosteo(models.Model):
    fecha = models.DateTimeField(auto_now_add=True)
    nota = models.CharField(max_length=300, blank=True, default='')
    resumen = models.JSONField()
    snapshot = models.JSONField()

    class Meta:
        ordering = ['-fecha']

    def __str__(self):
        return f'Snapshot {self.fecha:%d/%m/%Y}'