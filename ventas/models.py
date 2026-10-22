from django.db import models
from clientes.models import Cliente
from pacientes.models import Paciente
from productos.models import Producto, MovimientoInventario
from empleados.models import Empleado

class Venta(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('pagada', 'Pagada'),
        ('anulada', 'Anulada'),
    ]
    TIPO_PAGO_CHOICES = [
        ('efectivo', 'Efectivo'),
        ('tarjeta', 'Tarjeta'),
        ('transferencia', 'Transferencia'),
        ('mixto', 'Mixto'),
    ]
    numero = models.CharField(max_length=20, unique=True, verbose_name='No. Factura')
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='ventas')
    paciente = models.ForeignKey(Paciente, on_delete=models.SET_NULL, null=True, blank=True, related_name='ventas')
    empleado = models.ForeignKey(Empleado, on_delete=models.SET_NULL, null=True, related_name='ventas')
    fecha = models.DateTimeField(auto_now_add=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    descuento_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tipo_pago = models.CharField(max_length=15, choices=TIPO_PAGO_CHOICES, default='efectivo')
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='pendiente')
    notas = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Venta'
        verbose_name_plural = 'Ventas'
        ordering = ['-fecha']

    def __str__(self):
        return f'Venta #{self.numero} - {self.cliente} - Q{self.total}'

    def calcular_totales(self):
        subtotal = sum(item.subtotal for item in self.items.all())
        descuento = sum(item.descuento_monto for item in self.items.all())
        self.subtotal = subtotal
        self.descuento_total = descuento
        self.total = subtotal - descuento
        self.save()


class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='items')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    # Se conserva el costo vigente al registrar la venta para que las utilidades
    # históricas no cambien cuando se actualice el precio de compra del producto.
    costo_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    descuento_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='Descuento %')

    class Meta:
        verbose_name = 'Detalle de Venta'
        verbose_name_plural = 'Detalles de Venta'

    def __str__(self):
        return f'{self.producto} x{self.cantidad}'

    @property
    def subtotal(self):
        return self.precio_unitario * self.cantidad

    @property
    def descuento_monto(self):
        return self.subtotal * (self.descuento_pct / 100)

    @property
    def total(self):
        return self.subtotal - self.descuento_monto

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        if is_new and not self.costo_unitario:
            self.costo_unitario = self.producto.precio_compra
        super().save(*args, **kwargs)
        # Registrar movimiento de inventario si es nueva línea
        if is_new and self.producto.tipo != 'servicio':
            stock_anterior = self.producto.stock
            self.producto.stock -= self.cantidad
            self.producto.save()
            MovimientoInventario.objects.create(
                producto=self.producto,
                tipo='salida',
                cantidad=self.cantidad,
                stock_anterior=stock_anterior,
                stock_posterior=self.producto.stock,
                motivo='Venta',
                referencia=self.venta.numero,
            )

    @property
    def costo_total(self):
        return self.costo_unitario * self.cantidad

    @property
    def ganancia_bruta(self):
        return self.total - self.costo_total


class TransaccionHistorial(models.Model):
    """Historial unificado de todas las transacciones del sistema"""
    TIPO_CHOICES = [
        ('venta', 'Venta'),
        ('cita', 'Cita'),
        ('consulta', 'Consulta Médica'),
        ('inventario', 'Movimiento de Inventario'),
        ('compra', 'Compra a Proveedor'),
    ]
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    referencia_id = models.IntegerField(verbose_name='ID de referencia')
    descripcion = models.TextField()
    monto = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.SET_NULL, null=True, blank=True)
    paciente = models.ForeignKey(Paciente, on_delete=models.SET_NULL, null=True, blank=True)
    empleado = models.ForeignKey(Empleado, on_delete=models.SET_NULL, null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = 'Historial de Transacción'
        verbose_name_plural = 'Historial de Transacciones'
        ordering = ['-fecha']

    def __str__(self):
        return f'{self.get_tipo_display()} #{self.referencia_id} - {self.fecha.strftime("%d/%m/%Y")}'


class PagoNeonet(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('aceptado', 'Aceptado'),
        ('rechazado', 'Rechazado'),
        ('error', 'Error'),
    ]
    venta = models.ForeignKey(Venta, on_delete=models.PROTECT, related_name='pagos_neonet')
    referencia = models.CharField(max_length=50, unique=True)
    transaction_uuid = models.CharField(max_length=36, unique=True)
    estado = models.CharField(max_length=12, choices=ESTADO_CHOICES, default='pendiente')
    transaction_id = models.CharField(max_length=80, blank=True)
    razon = models.CharField(max_length=20, blank=True)
    mensaje = models.CharField(max_length=255, blank=True)
    respuesta = models.JSONField(default=dict, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Pago NeoNet'
        verbose_name_plural = 'Pagos NeoNet'

    def __str__(self):
        return f'NeoNet {self.referencia} ({self.estado})'
