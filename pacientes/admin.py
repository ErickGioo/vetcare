from django.contrib import admin
from .models import Especie, Raza, Paciente, HistorialMedico

admin.site.register(Especie)
admin.site.register(Raza)

@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'especie', 'propietario', 'estado']
    search_fields = ['nombre', 'propietario__nombre']
    list_filter = ['especie', 'estado']

@admin.register(HistorialMedico)
class HistorialAdmin(admin.ModelAdmin):
    list_display = ['paciente', 'motivo', 'fecha']
    readonly_fields = ['fecha']
