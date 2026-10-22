from django.db import models
from pacientes.models import Paciente
from empleados.models import Empleado

class Cita(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('confirmada', 'Confirmada'),
        ('en_curso', 'En curso'),
        ('completada', 'Completada'),
        ('cancelada', 'Cancelada'),
        ('no_asistio', 'No asistió'),
    ]
    TIPO_CHOICES = [
        ('consulta', 'Consulta general'),
        ('vacuna', 'Vacunación'),
        ('cirugia', 'Cirugía'),
        ('peluqueria', 'Grooming / peluquería'),
        ('bano', 'Baño'),
        ('corte_unas', 'Corte de uñas'),
        ('control', 'Control'),
        ('urgencia', 'Urgencia'),
        ('otro', 'Otro'),
    ]
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name='citas')
    veterinario = models.ForeignKey(Empleado, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='citas', verbose_name='Profesional responsable (opcional)')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='consulta')
    fecha_hora = models.DateTimeField(verbose_name='Fecha y hora')
    duracion_minutos = models.IntegerField(default=30, verbose_name='Duración (min)')
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='pendiente')
    motivo = models.CharField(max_length=300)
    notas = models.TextField(blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    recordatorio_enviado = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Cita'
        verbose_name_plural = 'Citas'
        ordering = ['-fecha_hora']

    def __str__(self):
        return f'{self.paciente} - {self.fecha_hora.strftime("%d/%m/%Y %H:%M")} ({self.get_estado_display()})'
