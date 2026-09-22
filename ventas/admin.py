from django.contrib import admin
from .models import Venta, DetalleVenta, PagoNeonet, TransaccionHistorial

class DetalleInline(admin.TabularInline):
    model = DetalleVenta
    extra = 0

@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ['numero', 'cliente', 'total', 'estado', 'fecha']
    list_filter = ['estado', 'tipo_pago']
    inlines = [DetalleInline]

@admin.register(TransaccionHistorial)
class TransaccionAdmin(admin.ModelAdmin):
    list_display = ['tipo', 'descripcion', 'monto', 'fecha']
    list_filter = ['tipo']
    readonly_fields = ['fecha']

@admin.register(PagoNeonet)
class PagoNeonetAdmin(admin.ModelAdmin):
    list_display = ['referencia', 'venta', 'estado', 'transaction_id', 'actualizado_en']
    list_filter = ['estado']
    readonly_fields = ['referencia', 'transaction_uuid', 'transaction_id', 'razon', 'mensaje', 'respuesta', 'creado_en', 'actualizado_en']
