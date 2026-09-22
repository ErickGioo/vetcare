from django.contrib import admin
from .models import Categoria, Producto, MovimientoInventario

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'activa']
    search_fields = ['nombre']

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre', 'tipo', 'categoria', 'precio_venta', 'stock', 'activo']
    list_filter = ['tipo', 'categoria', 'activo']
    search_fields = ['codigo', 'nombre']

@admin.register(MovimientoInventario)
class MovimientoAdmin(admin.ModelAdmin):
    list_display = ['producto', 'tipo', 'cantidad', 'stock_posterior', 'fecha']
    list_filter = ['tipo']
    readonly_fields = ['fecha']
