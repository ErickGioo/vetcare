from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django import forms
from .models import Empleado

class EmpleadoForm(forms.ModelForm):
    class Meta:
        model = Empleado
        fields = ['nombre', 'apellido', 'rol', 'especialidades', 'numero_colegiado',
                  'telefono', 'email', 'dpi', 'fecha_ingreso', 'activo', 'foto', 'notas']
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            if isinstance(f.widget, forms.CheckboxInput):
                f.widget.attrs['class'] = 'form-check-input'
            elif isinstance(f.widget, (forms.Select, forms.SelectMultiple)):
                f.widget.attrs['class'] = 'form-select'
            elif isinstance(f.widget, forms.Textarea):
                f.widget.attrs.update({'class': 'form-control', 'rows': 3})
            else:
                f.widget.attrs['class'] = 'form-control'

@login_required
def lista(request):
    empleados = Empleado.objects.filter(activo=True)
    return render(request, 'empleados/lista.html', {'empleados': empleados})

@login_required
def crear(request):
    form = EmpleadoForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        form.save()
        messages.success(request, 'Empleado registrado.')
        return redirect('empleados:lista')
    return render(request, 'empleados/form.html', {'form': form, 'titulo': 'Nuevo Empleado'})

@login_required
def editar(request, pk):
    empleado = get_object_or_404(Empleado, pk=pk)
    form = EmpleadoForm(request.POST or None, request.FILES or None, instance=empleado)
    if form.is_valid():
        form.save()
        messages.success(request, 'Empleado actualizado.')
        return redirect('empleados:lista')
    return render(request, 'empleados/form.html', {'form': form, 'titulo': 'Editar Empleado'})

@login_required
def detalle(request, pk):
    empleado = get_object_or_404(Empleado, pk=pk)
    citas = empleado.citas.all()[:10] if request.user.has_perm('citas.view_cita') else []
    return render(request, 'empleados/detalle.html', {'empleado': empleado, 'citas': citas})
