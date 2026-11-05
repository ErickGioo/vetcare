from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django import forms
from .models import Proveedor, Marca

class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = ['nombre', 'empresa', 'nit', 'telefono', 'email', 'direccion', 'contacto', 'marcas', 'activo', 'notas']
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
    from productos.models import Producto
    from django.db.models import Q
    productos = Producto.objects.filter(Q(proveedor=proveedor)|Q(proveedores=proveedor)).distinct() if request.user.has_perm('productos.view_producto') else []
    return render(request, 'proveedores/detalle.html', {'proveedor': proveedor, 'productos': productos})


class MarcaForm(forms.ModelForm):
    class Meta:
        model = Marca
        fields = ['nombre', 'activa']
        widgets = {'nombre': forms.TextInput(attrs={'class':'form-control'}),
                   'activa': forms.CheckboxInput(attrs={'class':'form-check-input'})}

    def clean_nombre(self):
        name = self.cleaned_data['nombre'].strip()
        if Marca.objects.filter(nombre__iexact=name).exists():
            raise forms.ValidationError('Esta marca ya existe.')
        return name


@login_required
@permission_required('proveedores.view_marca', raise_exception=True)
def marcas(request):
    from django.core.exceptions import PermissionDenied
    form = MarcaForm(request.POST or None)
    if request.method == 'POST':
        if not request.user.has_perm('proveedores.add_marca'):
            raise PermissionDenied
        if form.is_valid():
            form.save()
            messages.success(request, 'Marca registrada. Puedes utilizarla en productos y proveedores.')
            return redirect('proveedores:marcas')
    return render(request, 'proveedores/marcas.html', {'form':form, 'marcas':Marca.objects.all()})
