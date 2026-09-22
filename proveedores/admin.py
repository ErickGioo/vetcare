from django.contrib import admin
from .models import Proveedor

@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ['empresa', 'nombre', 'telefono', 'activo']
    search_fields = ['nombre', 'empresa']
