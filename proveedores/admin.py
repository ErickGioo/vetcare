from django.contrib import admin
from .models import Proveedor, Marca

@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ['empresa', 'nombre', 'telefono', 'activo']
    search_fields = ['nombre', 'empresa']


@admin.register(Marca)
class MarcaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'activa']
    search_fields = ['nombre']
