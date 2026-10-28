from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import Cliente
from .forms import ClienteForm

@login_required
def lista(request):
    query = request.GET.get('q', '')
    clientes = Cliente.objects.all()
    if query:
        clientes = clientes.filter(
            Q(nombre__icontains=query) | Q(apellido__icontains=query) |
            Q(telefono__icontains=query) | Q(nit__icontains=query)
        )
    return render(request, 'clientes/lista.html', {'clientes': clientes, 'query': query})

@login_required
def crear(request):
    form = ClienteForm(request.POST or None)
    if form.is_valid():
        cliente = form.save()
        messages.success(request, f'Cliente "{cliente}" registrado.')
        return redirect('clientes:lista')
    return render(request, 'clientes/form.html', {'form': form, 'titulo': 'Nuevo Cliente'})

@login_required
def editar(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    form = ClienteForm(request.POST or None, instance=cliente)
    if form.is_valid():
        form.save()
        messages.success(request, 'Cliente actualizado.')
        return redirect('clientes:lista')
    return render(request, 'clientes/form.html', {'form': form, 'titulo': 'Editar Cliente', 'cliente': cliente})

@login_required
def detalle(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    mascotas = cliente.mascotas.all() if request.user.has_perm('pacientes.view_paciente') else []
    ventas = cliente.ventas.all()[:10] if request.user.has_perm('ventas.view_venta') else []
    return render(request, 'clientes/detalle.html', {'cliente': cliente, 'mascotas': mascotas, 'ventas': ventas})

@login_required
def eliminar(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == 'POST':
        cliente.activo = False
        cliente.save()
        messages.success(request, 'Cliente desactivado.')
        return redirect('clientes:lista')
    return render(request, 'clientes/confirmar_eliminar.html', {'cliente': cliente})
