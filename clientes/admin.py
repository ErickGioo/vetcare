from django.contrib import admin
from .models import Cliente

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ['nombre_completo', 'telefono', 'email', 'activo']
    search_fields = ['nombre', 'apellido', 'telefono', 'nit']
    list_filter = ['activo']
