from django.db import models
from django.contrib.auth.models import User

class Especialidad(models.Model):
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre

class Empleado(models.Model):
    ROL_CHOICES = [
        ('veterinario', 'Médico Veterinario'),
        ('asistente', 'Asistente Veterinario'),
        ('recepcionista', 'Recepcionista'),
        ('farmaceutico', 'Farmacéutico'),
        ('admin', 'Administrador'),
    ]
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='empleado', null=True, blank=True)
    nombre = models.CharField(max_length=200)
    apellido = models.CharField(max_length=200)
    rol = models.CharField(max_length=20, choices=ROL_CHOICES)
    especialidades = models.ManyToManyField(Especialidad, blank=True)
    numero_colegiado = models.CharField(max_length=50, blank=True, verbose_name='No. Colegiado')
    telefono = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    dpi = models.CharField(max_length=20, blank=True, verbose_name='DPI')
    fecha_ingreso = models.DateField()
    activo = models.BooleanField(default=True)
    foto = models.ImageField(upload_to='empleados/', blank=True, null=True)
    notas = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Empleado'
        verbose_name_plural = 'Empleados'
        ordering = ['apellido', 'nombre']

    def __str__(self):
        return f'{self.get_rol_display()}: {self.nombre} {self.apellido}'

    @property
    def nombre_completo(self):
        return f'{self.nombre} {self.apellido}'
