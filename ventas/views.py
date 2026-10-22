from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django import forms
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import transaction
from django.db.models import Sum, Q
from django.http import HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from uuid import uuid4
from .models import Venta, DetalleVenta, PagoNeonet, TransaccionHistorial
from .neonet import checkout_fields, verify_response
from productos.models import Producto
from .operaciones import agregar_articulo, cambiar_cantidad, editable

class VentaForm(forms.ModelForm):
    class Meta:
        model = Venta
        fields = ['numero', 'cliente', 'paciente', 'empleado', 'tipo_pago', 'notas']
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            if isinstance(f.widget, (forms.Select,)):
                f.widget.attrs['class'] = 'form-select'
            elif isinstance(f.widget, forms.Textarea):
                f.widget.attrs.update({'class': 'form-control', 'rows': 2})
            else:
                f.widget.attrs['class'] = 'form-control'

@login_required
def lista(request):
    ventas = Venta.objects.select_related('cliente', 'empleado').all()
    total_mes = ventas.filter(estado='pagada').aggregate(t=Sum('total'))['t'] or 0
    return render(request, 'ventas/lista.html', {'ventas': ventas, 'total_mes': total_mes})

@login_required
def crear(request):
    form = VentaForm(request.POST or None)
    productos = Producto.objects.filter(activo=True, stock__gt=0)
    if form.is_valid():
        venta = form.save(commit=False)
        venta.estado = 'pendiente'
        venta.save()
        # Guardar historial
        TransaccionHistorial.objects.create(
            tipo='venta', referencia_id=venta.pk,
            descripcion=f'Venta #{venta.numero} - {venta.cliente}',
            monto=0, cliente=venta.cliente, paciente=venta.paciente,
            empleado=venta.empleado, usuario=request.user
        )
        messages.success(request, f'Venta #{venta.numero} creada. Agrega los productos.')
        return redirect('ventas:detalle', pk=venta.pk)
    return render(request, 'ventas/form.html', {'form': form, 'titulo': 'Nueva Venta', 'productos': productos})

@login_required
def detalle(request, pk):
    venta = get_object_or_404(Venta, pk=pk)
    if request.method == 'POST':
        try:
            if 'agregar_item' in request.POST:
                quantity = forms.IntegerField(min_value=1).clean(request.POST.get('cantidad'))
                product_id = forms.IntegerField(min_value=1).clean(request.POST.get('producto'))
                get_object_or_404(Producto, pk=product_id, activo=True)
                agregar_articulo(pk, product_id, quantity, request.user)
                messages.success(request, 'Artículo agregado y totales actualizados.')
            elif 'actualizar_item' in request.POST or 'eliminar_item' in request.POST:
                item_id = forms.IntegerField(min_value=1).clean(request.POST.get('item'))
                get_object_or_404(DetalleVenta, pk=item_id, venta_id=pk)
                quantity = 0 if 'eliminar_item' in request.POST else forms.IntegerField(min_value=1).clean(request.POST.get('cantidad'))
                cambiar_cantidad(pk, item_id, quantity, request.user)
                messages.success(request, 'Venta corregida. Inventario y totales actualizados.')
            elif 'actualizar_pago' in request.POST:
                method = forms.ChoiceField(choices=Venta.TIPO_PAGO_CHOICES).clean(request.POST.get('tipo_pago'))
                with transaction.atomic():
                    sale = Venta.objects.select_for_update().get(pk=pk)
                    editable(sale)
                    sale.tipo_pago = method
                    sale.save(update_fields=['tipo_pago'])
                messages.success(request, 'Forma de pago actualizada.')
        except ValidationError as error:
            messages.error(request, ' '.join(error.messages))
        return redirect('ventas:detalle', pk=pk)
    items = venta.items.select_related('producto').all()
    productos = Producto.objects.filter(activo=True).filter(Q(stock__gt=0) | Q(tipo='servicio'))
    return render(request, 'ventas/detalle.html', {'venta': venta, 'items': items, 'productos': productos, 'formas_pago':Venta.TIPO_PAGO_CHOICES})

@login_required
@require_POST
def confirmar_pago(request, pk):
    with transaction.atomic():
        venta = get_object_or_404(Venta.objects.select_for_update(), pk=pk)
        if venta.estado != 'pendiente':
            messages.info(request, 'Esta venta ya no está pendiente.')
            return redirect('ventas:detalle', pk=pk)
        if venta.pagos_neonet.filter(estado__in=['pendiente', 'aceptado']).exists():
            messages.error(request, 'Existe un pago con tarjeta en proceso; verifica su resultado antes de cobrar nuevamente.')
            return redirect('ventas:detalle', pk=pk)
        if venta.tipo_pago == 'tarjeta':
            messages.error(request, 'Los pagos con tarjeta deben confirmarse desde NeoNet.')
            return redirect('ventas:detalle', pk=pk)
        if not venta.items.exists() or venta.total <= 0:
            messages.error(request, 'Agrega artículos con un total mayor que cero antes de confirmar el pago.')
            return redirect('ventas:detalle', pk=pk)
        venta.estado = 'pagada'
        venta.save(update_fields=['estado'])
        TransaccionHistorial.objects.filter(tipo='venta', referencia_id=venta.pk).update(monto=venta.total)
    messages.success(request, f'Venta #{venta.numero} pagada. Total: Q{venta.total}')
    return redirect('ventas:detalle', pk=pk)


@login_required
@require_POST
@transaction.atomic
def iniciar_pago_neonet(request, pk):
    venta = get_object_or_404(Venta.objects.select_for_update(), pk=pk)
    if venta.estado != 'pendiente':
        messages.info(request, 'Esta venta ya fue pagada.')
        return redirect('ventas:detalle', pk=venta.pk)
    if not venta.items.exists() or venta.total <= 0:
        messages.error(request, 'Agrega productos antes de cobrar con tarjeta.')
        return redirect('ventas:detalle', pk=venta.pk)
    if not all((settings.NEONET_ACCESS_KEY, settings.NEONET_PROFILE_ID, settings.NEONET_SECRET_KEY)):
        messages.error(request, 'NeoNet no está configurado. Agrega las credenciales sandbox o productivas.')
        return redirect('ventas:detalle', pk=venta.pk)

    if venta.pagos_neonet.filter(estado__in=['pendiente', 'aceptado']).exists():
        messages.error(request, 'Ya existe un pago con tarjeta en proceso para esta venta.')
        return redirect('ventas:detalle', pk=pk)

    venta.tipo_pago = 'tarjeta'
    venta.save(update_fields=['tipo_pago'])
    pago = PagoNeonet.objects.create(
        venta=venta,
        referencia=f'{venta.numero}-{uuid4().hex[:12]}',
        transaction_uuid=str(uuid4()),
    )
    try:
        fields = checkout_fields(pago)
    except ImproperlyConfigured:
        pago.estado = 'error'
        pago.mensaje = 'Configuración de NeoNet incompleta.'
        pago.save(update_fields=['estado', 'mensaje', 'actualizado_en'])
        messages.error(request, pago.mensaje)
        return redirect('ventas:detalle', pk=venta.pk)
    return render(request, 'ventas/neonet_checkout.html', {
        'endpoint': settings.NEONET_ENDPOINT,
        'fields': fields,
        'venta': venta,
    })


@csrf_exempt
@require_POST
def respuesta_neonet(request):
    response = request.POST.dict()
    if not verify_response(response):
        return HttpResponseBadRequest('Firma de NeoNet inválida.')

    transaction_uuid = response.get('req_transaction_uuid') or response.get('transaction_uuid')
    if not transaction_uuid:
        return HttpResponseBadRequest('Respuesta de NeoNet sin identificador de transacción.')

    with transaction.atomic():
        pago = get_object_or_404(PagoNeonet.objects.select_for_update(), transaction_uuid=transaction_uuid)
        # La misma respuesta puede llegar más de una vez; no se duplica el cobro ni el historial.
        if pago.estado == 'aceptado':
            return render(request, 'ventas/neonet_resultado.html', {'pago': pago, 'venta': pago.venta})

        decision = response.get('decision', '').upper()
        pago.transaction_id = response.get('transaction_id', '')[:80]
        pago.razon = response.get('reason_code', '')[:20]
        pago.mensaje = response.get('message', '')[:255]
        pago.respuesta = {
            key: value for key, value in response.items()
            if key not in {'signature', 'card_number', 'card_cvn'}
        }
        pago.estado = 'aceptado' if decision == 'ACCEPT' else 'rechazado'
        pago.save()

        if pago.estado == 'aceptado':
            venta = pago.venta
            venta.estado = 'pagada'
            venta.tipo_pago = 'tarjeta'
            venta.save(update_fields=['estado', 'tipo_pago'])
            TransaccionHistorial.objects.filter(tipo='venta', referencia_id=venta.pk).update(monto=venta.total)
    return render(request, 'ventas/neonet_resultado.html', {'pago': pago, 'venta': pago.venta})

@login_required
def historial(request):
    transacciones = TransaccionHistorial.objects.select_related('cliente', 'paciente', 'empleado').all()
    return render(request, 'ventas/historial.html', {'transacciones': transacciones})


@login_required
def comprobante(request, pk):
    venta = get_object_or_404(Venta.objects.select_related('cliente', 'paciente'), pk=pk)
    return render(request, 'ventas/comprobante.html', {'venta': venta, 'items': venta.items.select_related('producto')})
