from django.contrib import admin
from .models import Cita

@admin.register(Cita)
class CitaAdmin(admin.ModelAdmin):
    list_display = ['paciente', 'veterinario', 'tipo', 'fecha_hora', 'estado']
    list_filter = ['estado', 'tipo']
    search_fields = ['paciente__nombre']
