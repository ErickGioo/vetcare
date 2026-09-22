from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import Paciente, HistorialMedico
from .forms import PacienteForm, HistorialMedicoForm, PostConsultaForm


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
    if form.is_valid():
        h = form.save(commit=False)
        h.paciente = paciente
        if not h.veterinario_id:
            h.veterinario = request.user
        h.save()
        messages.success(request, 'Consulta registrada correctamente.')
        return redirect('pacientes:detalle_historial', pk=pk, historial_pk=h.pk)
    return render(request, 'pacientes/historial_form.html', {'form': form, 'paciente': paciente})


@login_required
def detalle_historial(request, pk, historial_pk):
    paciente = get_object_or_404(Paciente, pk=pk)
    historial = get_object_or_404(HistorialMedico, pk=historial_pk, paciente=paciente)
    return render(request, 'pacientes/historial_detalle.html', {
        'paciente': paciente,
        'historial': historial,
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
        form.save()
        messages.success(request, 'Descripción post-consulta guardada.')
        return redirect('pacientes:detalle_historial', pk=pk, historial_pk=historial_pk)

    return render(request, 'pacientes/post_consulta_form.html', {
        'form': form,
        'paciente': paciente,
        'historial': historial,
    })
