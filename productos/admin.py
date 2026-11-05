from django.contrib import admin
from .models import Categoria, Producto, MovimientoInventario
from .forms import ProductoForm, CategoriaForm

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    form = CategoriaForm
    list_display = ['nombre', 'activa']
    search_fields = ['nombre']

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    form = ProductoForm
    fields = ProductoForm.Meta.fields
    list_display = ['codigo', 'nombre', 'tipo', 'categoria', 'precio_venta', 'stock', 'activo']
    list_filter = ['tipo', 'categoria', 'activo']
    search_fields = ['codigo', 'codigo_barras', 'nombre', 'marca__nombre']

    def save_model(self,request,obj,form,change):
        obj.tipo='servicio' if obj.categoria.es_servicio else (obj.tipo if obj.tipo!='servicio' else 'otro')
        super().save_model(request,obj,form,change)
        if obj.tipo!='servicio':
            from inventario.operaciones import asegurar_existencias
            asegurar_existencias(obj)

@admin.register(MovimientoInventario)
class MovimientoAdmin(admin.ModelAdmin):
    list_display = ['producto', 'tipo', 'cantidad', 'stock_posterior', 'fecha']
    list_filter = ['tipo']
    readonly_fields = ['fecha']
