from django.core.exceptions import ValidationError, PermissionDenied
from django.db import transaction
from django.db.models import Sum
from .models import Ubicacion, Existencia, Traslado


def ubicaciones_usuario(user):
    locations=Ubicacion.objects.filter(activa=True)
    if user.is_superuser:
        return locations
    assigned=locations.filter(usuarios=user)
    # Compatibilidad con las cuentas actuales, sin dar acceso a puntos nuevos.
    return assigned if assigned.exists() else locations.filter(central=True)


def validar_punto(user, location_id):
    if not ubicaciones_usuario(user).filter(pk=location_id).exists():
        raise PermissionDenied('No tienes acceso a este punto de venta.')


def sincronizar_total(product):
    from productos.models import Producto
    total=Existencia.objects.filter(producto=product).aggregate(n=Sum('cantidad'))['n'] or 0
    Producto.objects.filter(pk=product.pk).update(stock=total)
    product.stock=total


def asegurar_existencias(product):
    # Solo para registros nuevos; las ubicaciones históricas se migran explícitamente.
    central=Ubicacion.objects.get(central=True)
    if not Existencia.objects.filter(producto=product).exists():
        Existencia.objects.create(producto=product,ubicacion=central,cantidad=max(0,product.stock))
    return central


@transaction.atomic
def consumir(product, location_id, cantidad, user=None, referencia='', motivo='Venta'):
    from productos.models import Producto, MovimientoInventario
    product=Producto.objects.select_for_update().get(pk=product.pk)
    if product.tipo=='servicio' or cantidad==0:
        return
    asegurar_existencias(product)
    balance,_=Existencia.objects.get_or_create(producto=product,ubicacion_id=location_id,defaults={'cantidad':0})
    balance=Existencia.objects.select_for_update().get(pk=balance.pk)
    if cantidad>balance.cantidad:
        raise ValidationError(f'Stock insuficiente en {balance.ubicacion}. Disponible: {balance.cantidad}.')
    before=product.stock
    balance.cantidad-=cantidad
    balance.save(update_fields=['cantidad'])
    sincronizar_total(product)
    MovimientoInventario.objects.create(producto=product,tipo='salida' if cantidad>0 else 'entrada',cantidad=abs(cantidad),
        stock_anterior=before,stock_posterior=product.stock,motivo=motivo,referencia=referencia,usuario=user)


@transaction.atomic
def trasladar(product_id, origen_id, destino_id, cantidad, user, motivo, token):
    from productos.models import Producto
    if origen_id==destino_id or cantidad<1:
        raise ValidationError('Selecciona ubicaciones diferentes y una cantidad positiva.')
    if not Ubicacion.objects.filter(pk=origen_id,activa=True).exists() or not Ubicacion.objects.filter(pk=destino_id,activa=True).exists():
        raise ValidationError('Las ubicaciones deben estar activas.')
    product=Producto.objects.select_for_update().get(pk=product_id,activo=True)
    previous=Traslado.objects.filter(token=token).first()
    if previous:
        if (previous.producto_id,previous.origen_id,previous.destino_id,previous.cantidad,previous.usuario_id)!=(product_id,origen_id,destino_id,cantidad,user.pk):
            raise ValidationError('Esta operación ya fue utilizada.')
        return previous
    if product.tipo=='servicio':
        raise ValidationError('Los servicios no se trasladan ni manejan existencias.')
    asegurar_existencias(product)
    for location in sorted([origen_id,destino_id]):
        Existencia.objects.get_or_create(producto=product,ubicacion_id=location,defaults={'cantidad':0})
    origin=Existencia.objects.select_for_update().get(producto=product,ubicacion_id=origen_id)
    destination=Existencia.objects.select_for_update().get(producto=product,ubicacion_id=destino_id)
    if cantidad>origin.cantidad:
        raise ValidationError('No hay existencias suficientes en el origen.')
    origin.cantidad-=cantidad;destination.cantidad+=cantidad
    origin.save(update_fields=['cantidad']);destination.save(update_fields=['cantidad'])
    sincronizar_total(product)
    return Traslado.objects.create(token=token,producto=product,origen_id=origen_id,destino_id=destino_id,cantidad=cantidad,usuario=user,motivo=motivo)
