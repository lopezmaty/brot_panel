from django.db import models
from django.contrib.auth.models import User

TIPOS_MOVIMIENTO = [
    ('cobro_ventas', 'Cobro ventas'),
    ('pago_proveedor', 'Pago proveedor'),
    ('otro_egreso', 'Otro egreso'),
    ('otro_ingreso', 'Otro ingreso'),
    ('gasto_caja_chica', 'Gasto caja chica'),
    ('sueldo_jornal', 'Sueldo/Jornal'),
]

TIPOS_INGRESO = {'cobro_ventas', 'otro_ingreso'}
TIPOS_EGRESO = {'pago_proveedor', 'otro_egreso', 'gasto_caja_chica', 'sueldo_jornal'}


class SaldoInicial(models.Model):
    monto = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    actualizado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Saldo inicial'

    def __str__(self):
        return f'Saldo inicial: ${self.monto}'


class MovimientoCaja(models.Model):
    ESTADO = [
        ('parcial', 'Parcial'),
        ('completo', 'Completo'),
        ('bloqueado', 'Bloqueado'),
    ]

    fecha = models.DateField(null=True, blank=True)
    tipo = models.CharField(max_length=30, choices=TIPOS_MOVIMIENTO, blank=True)
    cliente_proveedor = models.CharField(max_length=100, blank=True)
    detalle = models.CharField(max_length=200, blank=True)
    nro_comprobante = models.CharField(max_length=50, blank=True)
    nro_recibo_op = models.CharField(max_length=50, blank=True)
    monto = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    conciliado = models.BooleanField(default=False)
    observaciones = models.CharField(max_length=300, blank=True)
    estado = models.CharField(max_length=10, choices=ESTADO, default='parcial')
    creado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='movimientos_creados'
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    modificado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['fecha', 'id']
        verbose_name = 'Movimiento de caja'

    def es_ingreso(self):
        return self.tipo in TIPOS_INGRESO

    def es_egreso(self):
        return self.tipo in TIPOS_EGRESO

    def campos_completos(self):
        return all([
            self.fecha,
            self.tipo,
            self.cliente_proveedor,
            self.nro_comprobante,
            self.nro_recibo_op,
            self.monto is not None,
        ])

    def nro_recibo_normalizado(self):
        """Normaliza 1-2520 → 0001-00002520 para comparar con Xubio."""
        if not self.nro_recibo_op:
            return ''
        partes = self.nro_recibo_op.strip().split('-')
        if len(partes) == 2:
            try:
                return f'{int(partes[0]):04d}-{int(partes[1]):08d}'
            except ValueError:
                pass
        return self.nro_recibo_op.strip()

    def __str__(self):
        return f'{self.fecha} | {self.tipo} | {self.cliente_proveedor} | ${self.monto}'


class CierreDiario(models.Model):
    fecha = models.DateField(unique=True)
    efectivo_contado = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    responsable = models.CharField(max_length=100, blank=True)
    observaciones = models.CharField(max_length=300, blank=True)
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    modificado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'Cierre diario'

    def __str__(self):
        return f'Cierre {self.fecha}'


class ConciliacionItem(models.Model):
    ESTADO = [
        ('ok', 'OK'),
        ('falta_en_caja', 'Falta en caja'),
        ('monto_difiere', 'Monto difiere'),
        ('falta_en_xubio', 'Falta en Xubio'),
    ]

    importacion_fecha = models.DateField(auto_now_add=True)
    fecha_xubio = models.DateField()
    nro_comprobante_xubio = models.CharField(max_length=50)
    cliente_xubio = models.CharField(max_length=100)
    importe_xubio = models.DecimalField(max_digits=14, decimal_places=2)
    movimiento_caja = models.ForeignKey(
        MovimientoCaja, on_delete=models.SET_NULL, null=True, blank=True
    )
    estado = models.CharField(max_length=20, choices=ESTADO)
    diferencia = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    class Meta:
        ordering = ['-importacion_fecha', 'fecha_xubio']
        verbose_name = 'Item de conciliación'

    def __str__(self):
        return f'{self.nro_comprobante_xubio} | {self.estado}'

# Create your models here.
