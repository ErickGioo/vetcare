from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import Producto, Categoria, MovimientoInventario
from .forms import ProductoForm, CategoriaForm, AjusteInventarioForm

@login_required
def lista_productos(request):
    query = request.GET.get('q', '')
    categoria_id = request.GET.get('categoria', '')
    tipo = request.GET.get('tipo', '')
    productos = Producto.objects.select_related('categoria', 'proveedor').all()
    if query:
        productos = productos.filter(Q(nombre__icontains=query) | Q(codigo__icontains=query))
    if categoria_id:
        productos = productos.filter(categoria_id=categoria_id)
    if tipo:
        productos = productos.filter(tipo=tipo)
    categorias = Categoria.objects.filter(activa=True)
    stock_bajo = Producto.objects.filter(activo=True).filter(stock__lte=5)
    return render(request, 'productos/lista.html', {
        'productos': productos,
        'categorias': categorias,
        'stock_bajo_count': stock_bajo.count(),
        'tipos': Producto.TIPO_CHOICES,
    })

@login_required
def crear_producto(request):
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES)
        if form.is_valid():
            producto = form.save()
            if producto.stock > 0:
                MovimientoInventario.objects.create(
                    producto=producto, tipo='entrada',
                    cantidad=producto.stock, stock_anterior=0,
                    stock_posterior=producto.stock,
                    motivo='Stock inicial', usuario=request.user
                )
            messages.success(request, f'Producto "{producto.nombre}" creado exitosamente.')
            return redirect('productos:lista')
    else:
        form = ProductoForm()
    return render(request, 'productos/form.html', {'form': form, 'titulo': 'Nuevo Producto'})

@login_required
def editar_producto(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES, instance=producto)
        if form.is_valid():
            form.save()
            messages.success(request, f'Producto "{producto.nombre}" actualizado.')
            return redirect('productos:lista')
    else:
        form = ProductoForm(instance=producto)
    return render(request, 'productos/form.html', {'form': form, 'titulo': 'Editar Producto', 'producto': producto})

@login_required
def eliminar_producto(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST':
        producto.activo = False
        producto.save()
        messages.success(request, f'Producto "{producto.nombre}" desactivado.')
        return redirect('productos:lista')
    return render(request, 'productos/confirmar_eliminar.html', {'producto': producto})

@login_required
def detalle_producto(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    movimientos = producto.movimientos.all()[:20]
    return render(request, 'productos/detalle.html', {'producto': producto, 'movimientos': movimientos})

@login_required
def ajustar_inventario(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST':
        form = AjusteInventarioForm(request.POST)
        if form.is_valid():
            tipo = form.cleaned_data['tipo']
            cantidad = form.cleaned_data['cantidad']
            stock_anterior = producto.stock
            if tipo == 'entrada':
                producto.stock += cantidad
            elif tipo == 'salida':
                if cantidad > producto.stock:
                    messages.error(request, 'No hay suficiente stock.')
                    return redirect('productos:ajustar_inventario', pk=pk)
                producto.stock -= cantidad
            else:
                producto.stock = cantidad
            producto.save()
            MovimientoInventario.objects.create(
                producto=producto, tipo=tipo, cantidad=cantidad,
                stock_anterior=stock_anterior, stock_posterior=producto.stock,
                motivo=form.cleaned_data['motivo'],
                referencia=form.cleaned_data.get('referencia', ''),
                usuario=request.user
            )
            messages.success(request, 'Inventario actualizado correctamente.')
            return redirect('productos:detalle', pk=pk)
    else:
        form = AjusteInventarioForm()
    return render(request, 'productos/ajustar_inventario.html', {'form': form, 'producto': producto})

@login_required
def lista_categorias(request):
    categorias = Categoria.objects.all()
    return render(request, 'productos/categorias.html', {'categorias': categorias})

@login_required
def crear_categoria(request):
    if request.method == 'POST':
        form = CategoriaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Categoría creada.')
            return redirect('productos:categorias')
    else:
        form = CategoriaForm()
    return render(request, 'productos/form_categoria.html', {'form': form, 'titulo': 'Nueva Categoría'})

@login_required
def editar_categoria(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    if request.method == 'POST':
        form = CategoriaForm(request.POST, instance=categoria)
        if form.is_valid():
            form.save()
            messages.success(request, 'Categoría actualizada.')
            return redirect('productos:categorias')
    else:
        form = CategoriaForm(instance=categoria)
    return render(request, 'productos/form_categoria.html', {'form': form, 'titulo': 'Editar Categoría'})
