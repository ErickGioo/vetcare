from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django import forms
from .models import Cita

class CitaForm(forms.ModelForm):
    class Meta:
        model = Cita
        fields = ['paciente', 'veterinario', 'tipo', 'fecha_hora', 'duracion_minutos', 'estado', 'motivo', 'notas']
        widgets = {'fecha_hora': forms.DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'type': 'datetime-local'})}
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            if isinstance(f.widget, (forms.Select,)):
                f.widget.attrs['class'] = 'form-select'
            elif isinstance(f.widget, forms.Textarea):
                f.widget.attrs.update({'class': 'form-control', 'rows': 3})
            else:
                f.widget.attrs['class'] = 'form-control'

@login_required
def lista(request):
    estado = request.GET.get('estado', '')
    citas = Cita.objects.select_related('paciente', 'veterinario').all()
    if estado:
        citas = citas.filter(estado=estado)
    return render(request, 'citas/lista.html', {'citas': citas, 'estados': Cita.ESTADO_CHOICES, 'estado_sel': estado})

@login_required
def crear(request):
    form = CitaForm(request.POST or None)
    if form.is_valid():
        cita = form.save()
        messages.success(request, f'Cita agendada para {cita.paciente}.')
        return redirect('citas:lista')
    return render(request, 'citas/form.html', {'form': form, 'titulo': 'Nueva Cita'})

@login_required
def editar(request, pk):
    cita = get_object_or_404(Cita, pk=pk)
    form = CitaForm(request.POST or None, instance=cita)
    if form.is_valid():
        form.save()
        messages.success(request, 'Cita actualizada.')
        return redirect('citas:lista')
    return render(request, 'citas/form.html', {'form': form, 'titulo': 'Editar Cita', 'cita': cita})

@login_required
def cambiar_estado(request, pk, estado):
    cita = get_object_or_404(Cita, pk=pk)
    cita.estado = estado
    cita.save()
    messages.success(request, f'Cita marcada como {cita.get_estado_display()}.')
    return redirect('citas:lista')
