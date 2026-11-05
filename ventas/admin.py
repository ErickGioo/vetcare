from django.contrib import admin
from .models import Venta, DetalleVenta, PagoNeonet, TransaccionHistorial

class DetalleInline(admin.TabularInline):
    model = DetalleVenta
    extra = 0
    readonly_fields = [f.name for f in DetalleVenta._meta.fields]

    def has_add_permission(self,request,obj=None): return False
    def has_change_permission(self,request,obj=None): return False
    def has_delete_permission(self,request,obj=None): return False

@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ['numero', 'cliente', 'total', 'estado', 'fecha']
    list_filter = ['estado', 'tipo_pago']
    inlines = [DetalleInline]
    readonly_fields = [f.name for f in Venta._meta.fields]

    def has_add_permission(self,request): return False
    def has_change_permission(self,request,obj=None): return False
    def has_delete_permission(self,request,obj=None): return False

@admin.register(TransaccionHistorial)
class TransaccionAdmin(admin.ModelAdmin):
    list_display = ['tipo', 'descripcion', 'monto', 'fecha']
    list_filter = ['tipo']
    readonly_fields = ['fecha']

@admin.register(PagoNeonet)
class PagoNeonetAdmin(admin.ModelAdmin):
    list_display = ['referencia', 'venta', 'estado', 'transaction_id', 'actualizado_en']
    list_filter = ['estado']
    readonly_fields = [f.name for f in PagoNeonet._meta.fields]

    def has_add_permission(self,request): return False
    def has_change_permission(self,request,obj=None): return False
    def has_delete_permission(self,request,obj=None): return False
