from uuid import uuid4
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError, PermissionDenied
from django.contrib import messages
from django.shortcuts import render, redirect
from productos.models import Producto
from .models import Ubicacion, Existencia, Traslado
from .forms import PuntoForm, TrasladoForm
from .operaciones import trasladar, ubicaciones_usuario


@login_required
@permission_required('inventario.view_existencia',raise_exception=True)
def panel(request):
    form=TrasladoForm(request.POST if request.method=='POST' else None,initial={'token':uuid4()})
    allowed=ubicaciones_usuario(request.user)
    if not request.user.is_superuser and not request.user.has_perm('inventario.add_traslado'):
        form.fields['origen'].queryset=allowed
        form.fields['destino'].queryset=allowed
    if request.method=='POST':
        if not request.user.has_perm('inventario.add_traslado'):
            raise PermissionDenied
        if form.is_valid():
            data=form.cleaned_data
            try:
                traslado=trasladar(data['producto'].pk,data['origen'].pk,data['destino'].pk,data['cantidad'],request.user,data['motivo'],data['token'])
                messages.success(request,f'Traslado #{traslado.pk} registrado. Las unidades se movieron sin duplicarse.')
                return redirect('inventario:panel')
            except ValidationError as error:
                form.add_error(None,error)
    # Ver toda la red requiere permiso explícito de traslado; vendedores ven sus ubicaciones.
    locations=Ubicacion.objects.filter(activa=True) if request.user.has_perm('inventario.add_traslado') else allowed
    stock=Existencia.objects.filter(ubicacion__in=locations).select_related('ubicacion','producto','producto__marca').order_by('ubicacion__nombre','producto__nombre')
    query=request.GET.get('q','').strip()
    if query:
        from django.db.models import Q
        stock=stock.filter(Q(producto__nombre__icontains=query)|Q(producto__codigo=query)|Q(producto__codigo_barras=query))
    from django.core.paginator import Paginator
    transfers=Traslado.objects.filter(origen__in=locations,destino__in=locations).select_related('origen','destino','producto','usuario')[:30]
    return render(request,'inventario/panel.html',{'form':form,'stock':Paginator(stock,50).get_page(request.GET.get('page')),'traslados':transfers})


@login_required
@permission_required('inventario.view_ubicacion',raise_exception=True)
def puntos(request):
    form=PuntoForm(request.POST or None)
    if request.method=='POST':
        if not request.user.has_perm('inventario.add_ubicacion'):
            raise PermissionDenied
        if form.is_valid():
            form.save()
            messages.success(request,'Punto de venta creado. Asígnale inventario mediante un traslado.')
            return redirect('inventario:puntos')
    return render(request,'inventario/puntos.html',{'form':form,'puntos':Ubicacion.objects.prefetch_related('usuarios').all() if request.user.has_perm('inventario.add_ubicacion') else ubicaciones_usuario(request.user)})


@login_required
@permission_required('inventario.change_ubicacion',raise_exception=True)
def editar_punto(request,pk):
    from django.shortcuts import get_object_or_404
    point=get_object_or_404(Ubicacion,pk=pk)
    form=PuntoForm(request.POST or None,instance=point)
    if request.method=='POST' and form.is_valid():
        form.save()
        messages.success(request,'Usuarios y nombre del punto actualizados.')
        return redirect('inventario:puntos')
    return render(request,'inventario/editar_punto.html',{'form':form,'punto':point})
