from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django import forms
from .models import Proveedor

class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = ['nombre', 'empresa', 'nit', 'telefono', 'email', 'direccion', 'contacto', 'activo', 'notas']
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            if isinstance(f.widget, forms.CheckboxInput):
                f.widget.attrs['class'] = 'form-check-input'
            elif isinstance(f.widget, forms.Textarea):
                f.widget.attrs.update({'class': 'form-control', 'rows': 3})
            else:
                f.widget.attrs['class'] = 'form-control'

@login_required
def lista(request):
    proveedores = Proveedor.objects.all()
    return render(request, 'proveedores/lista.html', {'proveedores': proveedores})

@login_required
def crear(request):
    form = ProveedorForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, 'Proveedor registrado.')
        return redirect('proveedores:lista')
    return render(request, 'proveedores/form.html', {'form': form, 'titulo': 'Nuevo Proveedor'})

@login_required
def editar(request, pk):
    proveedor = get_object_or_404(Proveedor, pk=pk)
    form = ProveedorForm(request.POST or None, instance=proveedor)
    if form.is_valid():
        form.save()
        messages.success(request, 'Proveedor actualizado.')
        return redirect('proveedores:lista')
    return render(request, 'proveedores/form.html', {'form': form, 'titulo': 'Editar Proveedor'})

@login_required
def detalle(request, pk):
    proveedor = get_object_or_404(Proveedor, pk=pk)
    productos = proveedor.producto_set.all() if request.user.has_perm('productos.view_producto') else []
    return render(request, 'proveedores/detalle.html', {'proveedor': proveedor, 'productos': productos})
