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
