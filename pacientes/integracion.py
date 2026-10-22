from datetime import datetime
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from citas.models import Cita
from empleados.models import Empleado
from ventas.models import Venta, DetalleVenta, TransaccionHistorial
from productos.models import Producto
from .models import HistorialMedico


@transaction.atomic
def facturar_consulta(history_id, service_id, user):
    history = HistorialMedico.objects.select_for_update().select_related('paciente').get(pk=history_id)
    if history.venta_id:
        return history.venta
    service = Producto.objects.select_for_update().get(pk=service_id)
    if not service.activo or service.tipo != 'servicio' or service.precio_final <= 0:
        raise ValidationError('Selecciona un servicio activo con tarifa mayor que cero.')
    employee = Empleado.objects.filter(usuario_id=history.veterinario_id, activo=True).first()
    sale = Venta.objects.create(numero=f'C{history.pk}-{uuid4().hex[:10]}', cliente_id=history.paciente.propietario_id,
        paciente=history.paciente, empleado=employee, estado='pendiente',
        notas=f'Atención veterinaria #{history.pk}')
    item = DetalleVenta.objects.create(venta=sale, producto=service, cantidad=1,
        precio_unitario=service.precio_venta, descuento_pct=service.descuento)
    sale.calcular_totales()
    TransaccionHistorial.objects.create(tipo='venta', referencia_id=sale.pk,
        descripcion=f'Consulta #{history.pk} · Venta {sale.numero}', monto=sale.total,
        cliente=sale.cliente, paciente=history.paciente, empleado=employee, usuario=user)
    history.venta = sale
    history.detalle_servicio = item
    history.save(update_fields=['venta', 'detalle_servicio'])
    return sale


@transaction.atomic
def sincronizar_revision(history_id):
    history = HistorialMedico.objects.select_for_update().get(pk=history_id)
    appointment = Cita.objects.select_for_update().filter(pk=history.cita_revision_id).first()
    if not history.proxima_cita:
        if appointment and appointment.estado in ('pendiente', 'confirmada'):
            appointment.estado = 'cancelada'
            appointment.save(update_fields=['estado'])
        return appointment
    if not history.proxima_hora:
        raise ValidationError('Indica la hora de la cita de revisión.')
    when = timezone.make_aware(datetime.combine(history.proxima_cita, history.proxima_hora))
    if appointment and appointment.estado in ('en_curso', 'completada', 'no_asistio'):
        if appointment.fecha_hora != when:
            raise ValidationError('La revisión vinculada ya fue atendida o iniciada; agenda otra desde Citas.')
        return appointment
    employee = Empleado.objects.filter(usuario_id=history.veterinario_id, activo=True).first()
    if not appointment:
        appointment = Cita.objects.create(paciente_id=history.paciente_id, veterinario=employee,
            tipo='control', fecha_hora=when, estado='pendiente',
            motivo=history.motivo_proxima_cita or 'Revisión posterior a consulta')
        history.cita_revision = appointment
        history.save(update_fields=['cita_revision'])
    else:
        changed_date = appointment.fecha_hora != when
        appointment.fecha_hora = when
        appointment.veterinario = employee
        appointment.motivo = history.motivo_proxima_cita or 'Revisión posterior a consulta'
        if changed_date and appointment.estado == 'cancelada':
            appointment.estado = 'pendiente'
        appointment.save()
    return appointment
