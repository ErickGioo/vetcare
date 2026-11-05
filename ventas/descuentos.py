import hashlib
import json
from decimal import Decimal
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import transaction
from django.utils import timezone
from caja.operaciones import puede_autorizar
from inventario.operaciones import validar_punto
from .models import Venta, SolicitudDescuento
from .operaciones import editable, actualizar_totales

LIMITE=Decimal('5.00')


def huella(sale):
    payload={'punto':sale.punto_venta_id,'mayorista':sale.mayorista,'total':f'{sale.total:.2f}',
        'items':list(sale.items.order_by('pk').values('pk','producto_id','cantidad','precio_unitario','descuento_pct'))}
    return hashlib.sha256(json.dumps(payload,sort_keys=True,default=str).encode()).hexdigest()


def validar_descuento(sale):
    if sale.items.filter(descuento_pct__gte=LIMITE).exists():
        if not sale.solicitudes_descuento.filter(estado='aprobada',huella=huella(sale)).exists():
            raise ValidationError('El descuento es del 5 % o más y requiere aprobación del administrador. No se puede cobrar todavía.')


@transaction.atomic
def aplicar_descuento(sale_id,porcentaje,motivo,user):
    sale=Venta.objects.select_for_update().get(pk=sale_id)
    validar_punto(user,sale.punto_venta_id)
    editable(sale)
    if not sale.items.exists():
        raise ValidationError('Agrega artículos antes de solicitar el descuento.')
    if not Decimal('0')<=porcentaje<=Decimal('100'):
        raise ValidationError('El descuento debe estar entre 0 y 100 %.')
    if porcentaje>=LIMITE and not motivo.strip():
        raise ValidationError('Indica el motivo para el administrador.')
    sale.items.update(descuento_pct=porcentaje)
    actualizar_totales(sale)
    if porcentaje<LIMITE:
        return None
    fingerprint=huella(sale)
    previous=sale.solicitudes_descuento.filter(huella=fingerprint,estado='pendiente').first()
    if previous:
        return previous
    return SolicitudDescuento.objects.create(venta=sale,porcentaje=porcentaje,motivo=motivo.strip(),huella=fingerprint,
        total_solicitado=sale.total,solicitada_por=user)


@transaction.atomic
def resolver_descuento(request_id,user,aprobar):
    if not puede_autorizar(user):
        raise PermissionDenied('Solo un administrador puede autorizar descuentos.')
    # Mismo orden de bloqueo que edición y solicitud: venta, luego solicitud.
    reference=SolicitudDescuento.objects.get(pk=request_id)
    sale=Venta.objects.select_for_update().get(pk=reference.venta_id)
    validar_punto(user,sale.punto_venta_id)
    request=SolicitudDescuento.objects.select_for_update().get(pk=request_id)
    if request.estado!='pendiente':
        raise ValidationError('Esta solicitud ya fue resuelta.')
    editable(sale)
    if request.huella!=huella(sale):
        raise ValidationError('La venta cambió. Solicita nuevamente el descuento para los artículos actuales.')
    request.estado='aprobada' if aprobar else 'rechazada'
    request.resuelta_por=user;request.resuelta_en=timezone.now()
    request.save(update_fields=['estado','resuelta_por','resuelta_en'])
    return request
