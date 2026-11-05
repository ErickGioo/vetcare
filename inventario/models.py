from django.conf import settings
from django.db import models
from django.db.models import Q


class Ubicacion(models.Model):
    nombre = models.CharField(max_length=150, unique=True)
    central = models.BooleanField(default=False)
    activa = models.BooleanField(default=True)
    usuarios = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='puntos_venta')

    class Meta:
        ordering = ['-central','nombre']
        constraints = [models.UniqueConstraint(fields=['central'], condition=Q(central=True), name='un_almacen_central')]

    def __str__(self):
        return self.nombre


class Existencia(models.Model):
    ubicacion = models.ForeignKey(Ubicacion, on_delete=models.PROTECT, related_name='existencias')
    producto = models.ForeignKey('productos.Producto', on_delete=models.PROTECT, related_name='existencias')
    cantidad = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['ubicacion','producto'], name='stock_unico_ubicacion_producto')]


class Traslado(models.Model):
    token = models.UUIDField(unique=True)
    origen = models.ForeignKey(Ubicacion, on_delete=models.PROTECT, related_name='traslados_salida')
    destino = models.ForeignKey(Ubicacion, on_delete=models.PROTECT, related_name='traslados_entrada')
    producto = models.ForeignKey('productos.Producto', on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField()
    motivo = models.CharField(max_length=300)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha','-pk']
