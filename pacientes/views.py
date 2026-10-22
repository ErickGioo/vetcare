from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.db.models import Q
from .models import Especie, Paciente, HistorialMedico, Raza
from .forms import EspecieForm, PacienteForm, HistorialMedicoForm, PostConsultaForm, RazaForm
from .forms import ServicioConsultaForm, ServicioRapidoForm
from .integracion import facturar_consulta, sincronizar_revision
from django.db import transaction
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET


staff_required = user_passes_test(lambda user: user.is_staff)


@login_required
def lista(request):
    query = request.GET.get('q', '')
    pacientes = Paciente.objects.select_related('propietario', 'especie', 'raza').filter(estado='activo')
    if query:
        pacientes = pacientes.filter(
            Q(nombre__icontains=query) |
            Q(propietario__nombre__icontains=query) |
            Q(propietario__apellido__icontains=query)
        )
    return render(request, 'pacientes/lista.html', {'pacientes': pacientes, 'query': query})


@login_required
def crear(request):
    form = PacienteForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        paciente = form.save()
        messages.success(request, f'Paciente "{paciente.nombre}" registrado.')
        return redirect('pacientes:detalle', pk=paciente.pk)
    return render(request, 'pacientes/form.html', {'form': form, 'titulo': 'Nuevo Paciente'})


@login_required
def editar(request, pk):
    paciente = get_object_or_404(Paciente, pk=pk)
    form = PacienteForm(request.POST or None, request.FILES or None, instance=paciente)
    if form.is_valid():
        form.save()
        messages.success(request, 'Paciente actualizado.')
        return redirect('pacientes:detalle', pk=pk)
    return render(request, 'pacientes/form.html', {'form': form, 'titulo': 'Editar Paciente', 'paciente': paciente})


@login_required
def detalle(request, pk):
    paciente = get_object_or_404(Paciente, pk=pk)
    historial = paciente.historial.select_related('veterinario').all()
    citas = paciente.citas.all()[:5]
    ventas = paciente.ventas.all()[:5]
    return render(request, 'pacientes/detalle.html', {
        'paciente': paciente,
        'historial': historial,
        'citas': citas,
        'ventas': ventas,
    })


@login_required
def agregar_historial(request, pk):
    paciente = get_object_or_404(Paciente, pk=pk)
    form = HistorialMedicoForm(request.POST or None)
    billing = ServicioConsultaForm(request.POST or None)
    if request.method == 'POST' and form.is_valid() and billing.is_valid():
        try:
            with transaction.atomic():
                h = form.save(commit=False)
                h.paciente = paciente
                if not h.veterinario_id:
                    h.veterinario = request.user
                h.save()
                facturar_consulta(h.pk, billing.cleaned_data['servicio'].pk, request.user)
                sincronizar_revision(h.pk)
            messages.success(request, 'Consulta registrada con venta pendiente y revisión agendada, si fue indicada.')
            return redirect('pacientes:detalle_historial', pk=pk, historial_pk=h.pk)
        except ValidationError as error:
            form.add_error(None, error)
    return render(request, 'pacientes/historial_form.html', {'form': form, 'paciente': paciente, 'billing': billing})


@login_required
def detalle_historial(request, pk, historial_pk):
    paciente = get_object_or_404(Paciente, pk=pk)
    historial = get_object_or_404(HistorialMedico, pk=historial_pk, paciente=paciente)
    return render(request, 'pacientes/historial_detalle.html', {
        'paciente': paciente,
        'historial': historial,
        'billing': ServicioConsultaForm(),
    })


@login_required
def post_consulta(request, pk, historial_pk):
    """El médico completa la descripción post-consulta y cierra la consulta."""
    paciente = get_object_or_404(Paciente, pk=pk)
    historial = get_object_or_404(HistorialMedico, pk=historial_pk, paciente=paciente)

    if historial.consulta_cerrada:
        messages.warning(request, 'Esta consulta ya está cerrada.')
        return redirect('pacientes:detalle_historial', pk=pk, historial_pk=historial_pk)

    form = PostConsultaForm(request.POST or None, instance=historial)
    if form.is_valid():
        try:
            with transaction.atomic():
                locked = HistorialMedico.objects.select_for_update().get(pk=historial_pk)
                if locked.consulta_cerrada:
                    raise ValidationError('Esta consulta ya está cerrada.')
                form.instance.venta_id = locked.venta_id
                form.instance.detalle_servicio_id = locked.detalle_servicio_id
                form.instance.cita_revision_id = locked.cita_revision_id
                form.save()
                sincronizar_revision(historial_pk)
            messages.success(request, 'Postconsulta guardada. La revisión indicada ya aparece en Citas.')
            return redirect('pacientes:detalle_historial', pk=pk, historial_pk=historial_pk)
        except ValidationError as error:
            form.add_error(None, error)

    return render(request, 'pacientes/post_consulta_form.html', {
        'form': form,
        'paciente': paciente,
        'historial': historial,
    })


@login_required
@require_GET
def razas(request):
    species = request.GET.get('especie', '')
    if not species.isdigit():
        return JsonResponse({'razas': []})
    breeds = Raza.objects.filter(especie_id=species, nombre__istartswith=request.GET.get('q', '').strip()[:100]).order_by('nombre')[:100]
    return JsonResponse({'razas': list(breeds.values('id', 'nombre'))})


@login_required
@require_POST
def crear_servicio(request):
    if not request.user.is_staff:
        return JsonResponse({'error': 'Solo un administrador puede crear tarifas.'}, status=403)
    form = ServicioRapidoForm(request.POST)
    if not form.is_valid():
        return JsonResponse({'error': 'Revisa el nombre y los importes.', 'errores': form.errors}, status=400)
    from productos.models import Producto
    from uuid import uuid4
    from decimal import Decimal
    name, price = form.cleaned_data['nombre'], form.cleaned_data['precio']
    cost = form.cleaned_data['costo'] or Decimal('0')
    product = Producto.objects.filter(tipo='servicio', activo=True, nombre__iexact=name).first()
    if product and (product.precio_venta != price or product.precio_compra != cost or product.descuento != 0):
        return JsonResponse({'error': 'Ya existe un servicio con ese nombre y otra tarifa. Selecciónalo o modifica su precio en Productos.'}, status=400)
    if not product:
        product = Producto.objects.create(codigo='SERV-'+uuid4().hex[:12], nombre=name, tipo='servicio',
            precio_venta=price, precio_compra=cost, stock=0, stock_minimo=0, activo=True)
    return JsonResponse({'id':product.pk, 'nombre':product.nombre, 'precio':str(product.precio_final),
        'etiqueta': f'{product.nombre} · Q{product.precio_final:.2f}'})


@login_required
@require_POST
def facturar(request, pk, historial_pk):
    history = get_object_or_404(HistorialMedico, pk=historial_pk, paciente_id=pk)
    form = ServicioConsultaForm(request.POST)
    if form.is_valid():
        try:
            sale = facturar_consulta(history.pk, form.cleaned_data['servicio'].pk, request.user)
            return redirect('ventas:detalle', pk=sale.pk)
        except ValidationError as error:
            messages.error(request, ' '.join(error.messages))
    else:
        messages.error(request, 'Selecciona un servicio válido para facturar la atención.')
    return redirect('pacientes:detalle_historial', pk=pk, historial_pk=historial_pk)


@staff_required
def catalogos(request):
    """Catálogos clínicos disponibles únicamente para administradores del sistema."""
    especie_form = EspecieForm(prefix='especie')
    raza_form = RazaForm(prefix='raza')

    if request.method == 'POST':
        if 'guardar_especie' in request.POST:
            especie_form = EspecieForm(request.POST, prefix='especie')
            if especie_form.is_valid():
                especie_form.save()
                messages.success(request, 'Especie agregada correctamente.')
                return redirect('pacientes:catalogos')
        elif 'guardar_raza' in request.POST:
            raza_form = RazaForm(request.POST, prefix='raza')
            if raza_form.is_valid():
                raza_form.save()
                messages.success(request, 'Raza agregada correctamente.')
                return redirect('pacientes:catalogos')

    especies = Especie.objects.prefetch_related('razas').order_by('nombre')
    return render(request, 'pacientes/catalogos.html', {
        'especie_form': especie_form,
        'raza_form': raza_form,
        'especies': especies,
    })
