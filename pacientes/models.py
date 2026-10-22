from django.db import models
from clientes.models import Cliente

class Especie(models.Model):
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre

class Raza(models.Model):
    especie = models.ForeignKey(Especie, on_delete=models.CASCADE, related_name='razas')
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return f'{self.nombre} ({self.especie})'

class Paciente(models.Model):
    SEXO_CHOICES = [('M', 'Macho'), ('H', 'Hembra')]
    ESTADO_CHOICES = [
        ('activo', 'Activo'),
        ('fallecido', 'Fallecido'),
        ('perdido', 'Perdido'),
        ('transferido', 'Transferido'),
    ]
    propietario = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='mascotas')
    nombre = models.CharField(max_length=100)
    especie = models.ForeignKey(Especie, on_delete=models.SET_NULL, null=True)
    raza = models.ForeignKey(Raza, on_delete=models.SET_NULL, null=True, blank=True)
    sexo = models.CharField(max_length=1, choices=SEXO_CHOICES)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    color = models.CharField(max_length=100, blank=True)
    peso = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, help_text='kg')
    esterilizado = models.BooleanField(default=False)
    microchip = models.CharField(max_length=50, blank=True)
    alergias = models.TextField(blank=True)
    condiciones_cronicas = models.TextField(blank=True, verbose_name='Condiciones crónicas')
    foto = models.ImageField(upload_to='pacientes/', blank=True, null=True)
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='activo')
    fecha_registro = models.DateTimeField(auto_now_add=True)
    notas = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Paciente'
        verbose_name_plural = 'Pacientes'
        ordering = ['nombre']

    def __str__(self):
        return f'{self.nombre} ({self.propietario})'


class HistorialMedico(models.Model):
    ESTADO_CHOICES = [
        ('abierta', 'Consulta abierta'),
        ('cerrada', 'Cerrada / Finalizada'),
        ('seguimiento', 'En seguimiento'),
    ]

    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name='historial')
    fecha = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    # --- Datos de la consulta ---
    motivo = models.CharField(max_length=300, verbose_name='Motivo de consulta')
    anamnesis = models.TextField(blank=True, verbose_name='Anamnesis',
        help_text='Historia clínica relatada por el propietario')
    examen_fisico = models.TextField(blank=True, verbose_name='Examen físico',
        help_text='Hallazgos del examen físico general')
    peso_consulta = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True,
        verbose_name='Peso (kg)')
    temperatura = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True,
        verbose_name='Temperatura (°C)')
    frecuencia_cardiaca = models.IntegerField(null=True, blank=True,
        verbose_name='Frec. cardíaca (lpm)')
    frecuencia_respiratoria = models.IntegerField(null=True, blank=True,
        verbose_name='Frec. respiratoria (rpm)')

    # --- Diagnóstico ---
    diagnostico_presuntivo = models.TextField(blank=True, verbose_name='Diagnóstico presuntivo',
        help_text='Diagnóstico inicial antes de pruebas complementarias')
    diagnostico_definitivo = models.TextField(verbose_name='Diagnóstico definitivo',
        help_text='Diagnóstico confirmado al cierre de la consulta')
    examenes_solicitados = models.TextField(blank=True, verbose_name='Exámenes solicitados',
        help_text='Laboratorio, rayos X, ecografía, etc.')
    resultados_examenes = models.TextField(blank=True, verbose_name='Resultados de exámenes')

    # --- Tratamiento ---
    tratamiento = models.TextField(verbose_name='Plan de tratamiento')
    medicamentos = models.TextField(blank=True, verbose_name='Medicamentos recetados',
        help_text='Nombre, dosis, frecuencia y duración')
    cirugia_realizada = models.BooleanField(default=False, verbose_name='¿Se realizó cirugía?')
    detalle_cirugia = models.TextField(blank=True, verbose_name='Detalle de cirugía')

    # --- Descripción post-consulta (escrita por el médico al finalizar) ---
    descripcion_post_consulta = models.TextField(blank=True,
        verbose_name='Descripción post-consulta',
        help_text='Notas adicionales del médico tras finalizar la consulta: evolución esperada, '
                  'instrucciones al propietario, observaciones finales.')
    recomendaciones_propietario = models.TextField(blank=True,
        verbose_name='Recomendaciones al propietario',
        help_text='Cuidados en casa, dieta, restricciones de actividad, señales de alarma.')

    # --- Seguimiento ---
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='abierta',
        verbose_name='Estado de la consulta')
    proxima_cita = models.DateField(null=True, blank=True, verbose_name='Fecha próxima cita')
    motivo_proxima_cita = models.CharField(max_length=200, blank=True,
        verbose_name='Motivo próxima cita')
    proxima_hora = models.TimeField(null=True, blank=True, verbose_name='Hora de revisión')
    cita_revision = models.OneToOneField('citas.Cita', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='consulta_origen')
    venta = models.OneToOneField('ventas.Venta', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='consulta_origen')
    detalle_servicio = models.OneToOneField('ventas.DetalleVenta', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='consulta_facturada')

    veterinario = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='consultas', verbose_name='Médico tratante')
    observaciones = models.TextField(blank=True, verbose_name='Observaciones internas',
        help_text='Notas internas del equipo médico (no visibles al propietario)')

    class Meta:
        verbose_name = 'Historial Médico'
        verbose_name_plural = 'Historial Médico'
        ordering = ['-fecha']

    def __str__(self):
        return f'{self.paciente} — {self.fecha.strftime("%d/%m/%Y")} ({self.get_estado_display()})'

    @property
    def consulta_cerrada(self):
        return self.estado == 'cerrada'
