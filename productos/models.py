from django.db import models
from proveedores.models import Proveedor

class Categoria(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    activa = models.BooleanField(default=True)
    es_servicio = models.BooleanField(default=False, verbose_name="Servicios sin inventario")

    class Meta:
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    TIPO_CHOICES = [
        ('medicamento', 'Medicamento'),
        ('alimento', 'Alimento'),
        ('accesorio', 'Accesorio'),
        ('higiene', 'Higiene'),
        ('servicio', 'Servicio'),
        ('otro', 'Otro'),
    ]
    codigo = models.CharField(max_length=50, unique=True, verbose_name='Código')
    nombre = models.CharField(max_length=200)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='otro')
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, blank=True)
    proveedor = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, null=True, blank=True)
    descripcion = models.TextField(blank=True)
    precio_compra = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    precio_venta = models.DecimalField(max_digits=10, decimal_places=2)
    descuento = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text='Porcentaje de descuento')
    stock = models.IntegerField(default=0)
    stock_minimo = models.IntegerField(default=5, verbose_name='Stock mínimo')
    unidad_medida = models.CharField(max_length=30, default='unidad')
    requiere_receta = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)
    imagen = models.ImageField(upload_to='productos/', blank=True, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'
        ordering = ['nombre']

    def __str__(self):
        return f'{self.codigo} - {self.nombre}'

    @property
    def precio_final(self):
        if self.descuento > 0:
            return self.precio_venta * (1 - self.descuento / 100)
        return self.precio_venta

    @property
    def stock_bajo(self):
        return self.tipo != 'servicio' and self.stock <= self.stock_minimo


class MovimientoInventario(models.Model):
    TIPO_CHOICES = [
        ('entrada', 'Entrada'),
        ('salida', 'Salida'),
        ('ajuste', 'Ajuste'),
    ]
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='movimientos')
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    cantidad = models.IntegerField()
    stock_anterior = models.IntegerField()
    stock_posterior = models.IntegerField()
    motivo = models.CharField(max_length=200)
    referencia = models.CharField(max_length=100, blank=True, help_text='Nro. venta, compra, etc.')
    fecha = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)

    class Meta:
        verbose_name = 'Movimiento de Inventario'
        verbose_name_plural = 'Movimientos de Inventario'
        ordering = ['-fecha']

    def __str__(self):
        return f'{self.tipo} - {self.producto.nombre} ({self.cantidad})'
