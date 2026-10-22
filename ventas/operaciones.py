from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from productos.models import Producto, MovimientoInventario
from .models import Venta, DetalleVenta, TransaccionHistorial


def editable(sale):
    if sale.estado != 'pendiente':
        raise ValidationError('Solo se pueden modificar ventas pendientes. Una venta pagada requiere un proceso de devolución.')
    if sale.pagos_neonet.filter(estado__in=['pendiente', 'aceptado']).exists():
        raise ValidationError('Hay un pago con tarjeta en proceso. Finaliza su conciliación antes de modificar la venta.')


def actualizar_totales(sale):
    lines = list(sale.items.all())
    if any(line.cantidad <= 0 or line.precio_unitario < 0 or not 0 <= line.descuento_pct <= 100 for line in lines):
        raise ValidationError('Los artículos deben tener cantidad positiva, precio válido y descuento entre 0 y 100%.')
    if sum(line.subtotal for line in lines) > Decimal('99999999.99'):
        raise ValidationError('El subtotal supera el máximo permitido para una venta.')
    sale.calcular_totales()
    TransaccionHistorial.objects.filter(tipo='venta', referencia_id=sale.pk).update(monto=sale.total)


@transaction.atomic
def agregar_articulo(sale_id, product_id, quantity, user):
    sale = Venta.objects.select_for_update().get(pk=sale_id)
    editable(sale)
    if quantity < 1:
        raise ValidationError('La cantidad debe ser un entero mayor que cero.')
    product = Producto.objects.select_for_update().get(pk=product_id, activo=True)
    if product.tipo != 'servicio' and quantity > product.stock:
        raise ValidationError(f'Stock insuficiente. Disponible: {product.stock}.')
    item = DetalleVenta.objects.create(venta=sale, producto=product, cantidad=quantity,
        precio_unitario=product.precio_venta, descuento_pct=product.descuento)
    actualizar_totales(sale)
    return item


@transaction.atomic
def cambiar_cantidad(sale_id, item_id, quantity, user):
    sale = Venta.objects.select_for_update().get(pk=sale_id)
    editable(sale)
    item = DetalleVenta.objects.select_for_update().get(pk=item_id, venta=sale)
    if quantity < 0:
        raise ValidationError('La cantidad no puede ser negativa.')
    # The consultation service is retained; other lines can be removed.
    if quantity == 0 and hasattr(item, 'consulta_facturada'):
        raise ValidationError('El servicio vinculado a una consulta no puede eliminarse de su comprobante.')
    product = Producto.objects.select_for_update().get(pk=item.producto_id)
    difference = quantity - item.cantidad
    if product.tipo != 'servicio' and difference:
        if difference > product.stock:
            raise ValidationError(f'Stock insuficiente. Disponible: {product.stock}.')
        before = product.stock
        product.stock -= difference
        product.save(update_fields=['stock', 'fecha_actualizacion'])
        MovimientoInventario.objects.create(producto=product, tipo='salida' if difference > 0 else 'entrada',
            cantidad=abs(difference), stock_anterior=before, stock_posterior=product.stock,
            motivo='Corrección de cantidad en venta', referencia=sale.numero, usuario=user)
    if quantity == 0:
        item.delete()
    else:
        item.cantidad = quantity
        item.save(update_fields=['cantidad'])
    actualizar_totales(sale)
