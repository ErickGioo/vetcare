from django.db import models

class Cliente(models.Model):
    nombre = models.CharField(max_length=200)
    apellido = models.CharField(max_length=200)
    nit = models.CharField(max_length=20, blank=True, verbose_name='NIT')
    dpi = models.CharField(max_length=20, blank=True, verbose_name='DPI')
    telefono = models.CharField(max_length=20)
    telefono_alt = models.CharField(max_length=20, blank=True, verbose_name='Teléfono alternativo')
    email = models.EmailField(blank=True)
    direccion = models.TextField(blank=True)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    activo = models.BooleanField(default=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    notas = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['apellido', 'nombre']

    def __str__(self):
        return f'{self.nombre} {self.apellido}'

    @property
    def nombre_completo(self):
        return f'{self.nombre} {self.apellido}'
