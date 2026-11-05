from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django import forms
from django.conf import settings
from django.utils import timezone
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
from caja.operaciones import registrar_cobro
from inventario.operaciones import ubicaciones_usuario, validar_punto
from .descuentos import aplicar_descuento, validar_descuento, resolver_descuento, huella

class VentaForm(forms.ModelForm):
    class Meta:
        model = Venta
        fields = ['punto_venta', 'mayorista', 'cliente', 'paciente', 'empleado', 'tipo_pago', 'notas']
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            if isinstance(f.widget, forms.CheckboxInput):
                f.widget.attrs['class']='form-check-input'
            elif isinstance(f.widget, (forms.Select,)):
                f.widget.attrs['class'] = 'form-select'
            elif isinstance(f.widget, forms.Textarea):
                f.widget.attrs.update({'class': 'form-control', 'rows': 2})
            else:
                f.widget.attrs['class'] = 'form-control'

@login_required
def lista(request):
    ventas = Venta.objects.select_related('cliente', 'empleado').filter(punto_venta__in=ubicaciones_usuario(request.user))
    today = timezone.localdate()
    total_mes = ventas.filter(estado='pagada', fecha__date__gte=today.replace(day=1), fecha__date__lte=today).aggregate(t=Sum('total'))['t'] or 0
    canal=request.GET.get('canal','')
    if canal=='mayorista':
        ventas=ventas.filter(mayorista=True)
    estado = request.GET.get('estado', '')
    if estado in dict(Venta.ESTADO_CHOICES):
        ventas = ventas.filter(estado=estado)
    else:
        estado = ''
    return render(request, 'ventas/lista.html', {'ventas': ventas, 'total_mes': total_mes, 'estado': estado})

@login_required
def crear(request):
    form = VentaForm(request.POST or None,initial={'mayorista':request.GET.get('mayorista')=='1'})
    form.fields['punto_venta'].queryset=ubicaciones_usuario(request.user)
    if form.fields['punto_venta'].queryset.count()==1:
        form.fields['punto_venta'].initial=form.fields['punto_venta'].queryset.first().pk
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
    validar_punto(request.user,venta.punto_venta_id)
    if request.method == 'POST':
        try:
            if 'agregar_item' in request.POST:
                quantity = forms.IntegerField(min_value=1).clean(request.POST.get('cantidad'))
                barcode = request.POST.get('codigo_barras', '').strip()
                if barcode:
                    matches = list(Producto.objects.filter(activo=True).filter(Q(codigo=barcode)|Q(codigo_barras=barcode))[:2])
                    if len(matches) != 1:
                        raise ValidationError('Código no encontrado o ambiguo. Revisa el catálogo antes de agregarlo.')
                    product_id = matches[0].pk
                else:
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
            elif 'aplicar_descuento' in request.POST:
                from decimal import Decimal
                percentage=forms.DecimalField(min_value=Decimal('0'),max_value=Decimal('100'),max_digits=5,decimal_places=2).clean(request.POST.get('porcentaje'))
                approval=aplicar_descuento(pk,percentage,request.POST.get('motivo_descuento','')[:500],request.user)
                messages.success(request,'Solicitud registrada. Comparte el mensaje por WhatsApp para pedir autorización.' if approval else 'Descuento actualizado por debajo del umbral de autorización.')
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
    from inventario.models import Existencia
    productos = Producto.objects.filter(activo=True).filter(Q(existencias__ubicacion_id=venta.punto_venta_id,existencias__cantidad__gt=0)|Q(tipo='servicio')).distinct()
    if venta.mayorista:
        productos=productos.filter(precio_mayorista__gt=0)
    balances=dict(Existencia.objects.filter(ubicacion_id=venta.punto_venta_id,producto__in=productos).values_list('producto_id','cantidad'))
    for product in productos:
        product.stock_local=balances.get(product.pk,0)
        product.precio_aplicado=(product.precio_mayorista if venta.mayorista else product.precio_venta)*(1-product.descuento/100)
    from urllib.parse import urlencode
    approvals=list(venta.solicitudes_descuento.select_related('solicitada_por','resuelta_por')[:10])
    approval_url=request.build_absolute_uri('/ventas/descuentos/')
    for approval in approvals:
        approval.vigente=approval.huella==huella(venta)
        approval.whatsapp='https://wa.me/?'+urlencode({'text':f'Solicitud de descuento #{approval.pk}: venta {venta.numero}, {approval.porcentaje} %, total Q{approval.total_solicitado}. Autorizar con cuenta de administrador: {approval_url}'})
    return render(request, 'ventas/detalle.html', {'aprobaciones':approvals,'venta': venta, 'items': items, 'productos': productos, 'formas_pago':Venta.TIPO_PAGO_CHOICES})

@login_required
@require_POST
def confirmar_pago(request, pk):
    with transaction.atomic():
        venta = get_object_or_404(Venta.objects.select_for_update(), pk=pk)
        validar_punto(request.user,venta.punto_venta_id)
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
        try:
            validar_descuento(venta)
        except ValidationError as error:
            messages.error(request,' '.join(error.messages))
            return redirect('ventas:detalle',pk=pk)
        if venta.tipo_pago == 'mixto':
            messages.error(request, 'Para el cuadre de caja selecciona un método de pago único. Los pagos mixtos requieren un desglose que aún no está disponible.')
            return redirect('ventas:detalle', pk=pk)
        venta.estado = 'pagada'
        venta.save(update_fields=['estado'])
        registrar_cobro(venta)
        TransaccionHistorial.objects.filter(tipo='venta', referencia_id=venta.pk).update(monto=venta.total)
    messages.success(request, f'Venta #{venta.numero} pagada. Total: Q{venta.total}')
    return redirect('ventas:detalle', pk=pk)


@login_required
@require_POST
@transaction.atomic
def iniciar_pago_neonet(request, pk):
    venta = get_object_or_404(Venta.objects.select_for_update(), pk=pk)
    validar_punto(request.user,venta.punto_venta_id)
    if venta.estado != 'pendiente':
        messages.info(request, 'Esta venta ya fue pagada.')
        return redirect('ventas:detalle', pk=venta.pk)
    if not venta.items.exists() or venta.total <= 0:
        messages.error(request, 'Agrega productos antes de cobrar con tarjeta.')
        return redirect('ventas:detalle', pk=venta.pk)
    try:
        validar_descuento(venta)
    except ValidationError as error:
        messages.error(request,' '.join(error.messages))
        return redirect('ventas:detalle',pk=pk)
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
            venta = Venta.objects.select_for_update().get(pk=pago.venta_id)
            venta.estado = 'pagada'
            venta.tipo_pago = 'tarjeta'
            venta.save(update_fields=['estado', 'tipo_pago'])
            registrar_cobro(venta)
            TransaccionHistorial.objects.filter(tipo='venta', referencia_id=venta.pk).update(monto=venta.total)
    return render(request, 'ventas/neonet_resultado.html', {'pago': pago, 'venta': pago.venta})

@login_required
def historial(request):
    transacciones = TransaccionHistorial.objects.select_related('cliente', 'paciente', 'empleado').all()
    if not request.user.is_superuser:
        transacciones=transacciones.filter(tipo='venta',referencia_id__in=Venta.objects.filter(punto_venta__in=ubicaciones_usuario(request.user)).values('pk'))
    return render(request, 'ventas/historial.html', {'transacciones': transacciones})


@login_required
def comprobante(request, pk):
    venta = get_object_or_404(Venta.objects.select_related('cliente', 'paciente'), pk=pk)
    validar_punto(request.user,venta.punto_venta_id)
    return render(request, 'ventas/comprobante.html', {'venta': venta, 'items': venta.items.select_related('producto')})


@login_required
def descuentos(request):
    from django.core.exceptions import PermissionDenied
    from caja.operaciones import puede_autorizar
    from .models import SolicitudDescuento
    if not puede_autorizar(request.user):
        raise PermissionDenied('Solo administradores pueden revisar autorizaciones.')
    approvals=SolicitudDescuento.objects.filter(venta__punto_venta__in=ubicaciones_usuario(request.user)).select_related('venta','solicitada_por','resuelta_por')
    if request.method=='POST':
        if not request.user.has_perm('ventas.change_solicituddescuento'):
            raise PermissionDenied
        key=forms.IntegerField(min_value=1).clean(request.POST.get('solicitud'))
        approval=get_object_or_404(approvals,pk=key)
        decision=forms.ChoiceField(choices=[('aprobar','Aprobar'),('rechazar','Rechazar')]).clean(request.POST.get('decision'))
        try:
            resolver_descuento(approval.pk,request.user,decision=='aprobar')
            messages.success(request,'Decisión registrada. Ya puedes volver a la venta.')
        except ValidationError as error:
            messages.error(request,' '.join(error.messages))
        return redirect('ventas:descuentos')
    from django.core.paginator import Paginator
    return render(request,'ventas/descuentos.html',{'solicitudes':Paginator(approvals,30).get_page(request.GET.get('page'))})
