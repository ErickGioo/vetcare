from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from ventas.models import PagoNeonet
from .models import CajaDiaria, CobroCaja, ControlCaja

METODOS = ('efectivo', 'transferencia', 'tarjeta')


def bloquear():
    ControlCaja.objects.select_for_update().get(pk=1)


@transaction.atomic
def registrar_cobro(venta):
    bloquear()
    if CobroCaja.objects.filter(venta=venta).exists():
        return
    caja = CajaDiaria.objects.filter(fecha=timezone.localdate(), cerrada_en__isnull=True).first()
    # Un callback tardío se conserva fuera del cierre, sin alterar su cuadre.
    CobroCaja.objects.create(venta=venta, caja=caja, metodo=venta.tipo_pago, monto=venta.total)


def totales(caja):
    result = {method: Decimal('0') for method in METODOS}
    for cobro in caja.cobros.all():
        result[cobro.metodo] = result.get(cobro.metodo, Decimal('0')) + cobro.monto
    return result


@transaction.atomic
def abrir(usuario, inicial):
    bloquear()
    today = timezone.localdate()
    if CajaDiaria.objects.filter(fecha=today).exists():
        raise ValidationError('Ya existe una apertura para hoy. No se puede duplicar ni reabrir un cierre.')
    if CajaDiaria.objects.filter(cerrada_en__isnull=True).exists():
        raise ValidationError('Cierra la caja anterior antes de abrir una nueva.')
    caja = CajaDiaria.objects.create(fecha=today, inicial=inicial, abierta_por=usuario)
    CobroCaja.objects.filter(caja__isnull=True, fecha__date=today).update(caja=caja)
    return caja


@transaction.atomic
def cerrar(pk, usuario, contado, observaciones):
    bloquear()
    caja = CajaDiaria.objects.select_for_update().get(pk=pk)
    if caja.cerrada_en:
        raise ValidationError('Esta caja ya está cerrada. El cierre se conserva sin cambios.')
    if PagoNeonet.objects.filter(estado='pendiente').exists():
        raise ValidationError('Hay pagos NeoNet pendientes. Verifica su resultado antes de cerrar caja.')
    amounts = totales(caja)
    if any(key not in METODOS and value for key, value in amounts.items()):
        raise ValidationError('Hay cobros sin desglose por método; no se puede cerrar hasta aclararlos.')
    amounts['efectivo'] += caja.inicial
    caja.esperado = {key: str(amounts[key]) for key in METODOS}
    caja.contado = {key: str(contado[key]) for key in METODOS}
    caja.observaciones = observaciones
    caja.cerrada_en = timezone.now()
    caja.cerrada_por = usuario
    caja.save(update_fields=['esperado', 'contado', 'observaciones', 'cerrada_en', 'cerrada_por'])
    return caja


def puede_autorizar(usuario):
    return usuario.is_active and usuario.is_staff and (usuario.is_superuser or
        usuario.__class__.objects.filter(pk=usuario.pk, empleado__rol='admin', empleado__activo=True).exists())


@transaction.atomic
def solicitar_reapertura(pk, usuario, motivo):
    from .models import ReaperturaCaja
    bloquear()
    caja = CajaDiaria.objects.select_for_update().get(pk=pk)
    if not caja.cerrada_en:
        raise ValidationError('La caja ya está abierta.')
    if caja.reaperturas.filter(estado='pendiente').exists():
        raise ValidationError('Ya hay una solicitud pendiente para esta caja.')
    return ReaperturaCaja.objects.create(caja=caja, solicitada_por=usuario, motivo=motivo,
        cierre_referencia=caja.cerrada_en)


@transaction.atomic
def resolver_reapertura(pk, usuario, aprobar):
    from django.core.exceptions import PermissionDenied
    from .models import ReaperturaCaja
    if not puede_autorizar(usuario):
        raise PermissionDenied('Solo un administrador puede autorizar la reapertura.')
    bloquear()
    solicitud = ReaperturaCaja.objects.select_for_update().select_related('caja').get(pk=pk)
    caja = solicitud.caja
    if solicitud.estado != 'pendiente':
        raise ValidationError('Esta solicitud ya fue resuelta.')
    if aprobar:
        if caja.cerrada_en != solicitud.cierre_referencia:
            raise ValidationError('El cierre cambió; realiza una nueva solicitud.')
        if CajaDiaria.objects.filter(cerrada_en__isnull=True).exists():
            raise ValidationError('Cierra la caja abierta antes de autorizar esta reapertura.')
        solicitud.cierre_anterior = {'cerrada_en':caja.cerrada_en.isoformat(), 'cerrada_por':caja.cerrada_por_id,
            'esperado':caja.esperado, 'contado':caja.contado, 'observaciones':caja.observaciones,
            'inicial':str(caja.inicial), 'cobros':list(caja.cobros.values_list('pk',flat=True))}
        caja.cerrada_en = None
        caja.cerrada_por = None
        caja.esperado = {}
        caja.contado = {}
        caja.observaciones = ''
        caja.save(update_fields=['cerrada_en','cerrada_por','esperado','contado','observaciones'])
        CobroCaja.objects.filter(caja__isnull=True, fecha__date=caja.fecha).update(caja=caja)
    solicitud.estado = 'aprobada' if aprobar else 'rechazada'
    solicitud.resuelta_por = usuario
    solicitud.resuelta_en = timezone.now()
    solicitud.save(update_fields=['estado','resuelta_por','resuelta_en','cierre_anterior'])
    return solicitud
