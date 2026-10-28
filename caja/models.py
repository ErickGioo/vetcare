from django.conf import settings
from django.db import models


class ControlCaja(models.Model):
    """Fila única para serializar cobros, aperturas y cierres."""
    pass


class CajaDiaria(models.Model):
    fecha = models.DateField(unique=True)
    inicial = models.DecimalField(max_digits=14, decimal_places=2)
    abierta_en = models.DateTimeField(auto_now_add=True)
    abierta_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='cajas_abiertas')
    cerrada_en = models.DateTimeField(null=True, blank=True)
    cerrada_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name='cajas_cerradas')
    esperado = models.JSONField(default=dict)
    contado = models.JSONField(default=dict)
    observaciones = models.TextField(blank=True)

    class Meta:
        ordering = ['-fecha']


class CobroCaja(models.Model):
    venta = models.OneToOneField('ventas.Venta', on_delete=models.PROTECT, related_name='cobro_caja')
    caja = models.ForeignKey(CajaDiaria, on_delete=models.PROTECT, null=True, blank=True, related_name='cobros')
    fecha = models.DateTimeField(auto_now_add=True)
    metodo = models.CharField(max_length=15)
    monto = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ['-fecha', '-pk']


class AccesoSistema(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='accesos_sistema')
    fecha = models.DateTimeField(auto_now_add=True)
    pantalla = models.CharField(max_length=200)
    metodo = models.CharField(max_length=10)
    resultado = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ['-fecha', '-pk']
