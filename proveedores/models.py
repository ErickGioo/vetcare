from django.db import models

class Proveedor(models.Model):
    nombre = models.CharField(max_length=200)
    empresa = models.CharField(max_length=200, blank=True)
    nit = models.CharField(max_length=20, blank=True, verbose_name='NIT')
    telefono = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    direccion = models.TextField(blank=True)
    contacto = models.CharField(max_length=200, blank=True, verbose_name='Persona de contacto')
    activo = models.BooleanField(default=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    notas = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Proveedor'
        verbose_name_plural = 'Proveedores'
        ordering = ['nombre']

    def __str__(self):
        return self.empresa or self.nombre
