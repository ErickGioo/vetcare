from django.contrib import admin
from .models import Empleado, Especialidad

admin.site.register(Especialidad)

@admin.register(Empleado)
class EmpleadoAdmin(admin.ModelAdmin):
    list_display = ['nombre_completo', 'rol', 'telefono', 'activo']
    list_filter = ['rol', 'activo']
    search_fields = ['nombre', 'apellido']
