import calendar
import csv
from datetime import date, timedelta
from decimal import Decimal, ROUND_CEILING
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Sum, Count
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.cache import never_cache

from pacientes.models import HistorialMedico
from productos.models import Producto, MovimientoInventario
from ventas.models import Venta
from .views import _item_totals, _paid_items


def admin_report(view):
    @login_required
    @never_cache
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapped


def csv_report(filename, rows):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
    response.write('\ufeff')
    writer = csv.writer(response)
    for row in rows:
        writer.writerow(["'" + x if isinstance(x, str) and x.lstrip().startswith(('=', '+', '-', '@')) else x for x in row])
    return response


@admin_report
def cierre(request):
    today = timezone.localdate()
    monthly = request.GET.get('periodo') == 'mensual'
    try:
        selected = date.fromisoformat(request.GET.get('fecha', str(today)))
    except ValueError:
        selected = today
    start = selected.replace(day=1) if monthly else selected
    end = selected.replace(day=calendar.monthrange(selected.year, selected.month)[1]) if monthly else selected
    sales = Venta.objects.filter(fecha__date__range=(start, end))
    paid = sales.filter(estado='pagada')
    totals = _item_totals(_paid_items(start, end))
    totals['ingresos'] = paid.aggregate(value=Sum('total'))['value'] or Decimal('0.00')
    totals['ganancia'] = totals['ingresos'] - totals['costos']
    totals['margen'] = totals['ganancia'] / totals['ingresos'] * 100 if totals['ingresos'] else 0
    payments = list(paid.values('tipo_pago').annotate(cantidad=Count('pk'), total=Sum('total')).order_by('tipo_pago'))
    labels = dict(Venta.TIPO_PAGO_CHOICES)
    for payment in payments:
        payment['nombre'] = labels.get(payment['tipo_pago'], payment['tipo_pago'])
    pending = sales.filter(estado='pendiente').aggregate(cantidad=Count('pk'), total=Sum('total'))
    cancelled = sales.filter(estado='anulada').count()
    if request.GET.get('exportar') == 'csv':
        rows = [['Reporte de cierre', 'Mensual' if monthly else 'Diario'], ['Desde', str(start)], ['Hasta', str(end)],
                ['Ventas pagadas', paid.count()], ['Ingresos Q', totals['ingresos']], ['Costo Q', totals['costos']],
                ['Ganancia bruta Q', totals['ganancia']], ['Margen %', totals['margen']],
                ['Forma de pago', 'Cantidad', 'Total Q']]
        rows += [[p['nombre'], p['cantidad'], p['total']] for p in payments]
        rows += [[], ['Factura', 'Fecha de venta', 'Estado', 'Forma de pago', 'Total Q']]
        rows += [[v.numero, timezone.localtime(v.fecha).isoformat(), v.get_estado_display(), v.get_tipo_pago_display(), v.total] for v in sales]
        return csv_report(f'cierre-{start}-{end}', rows)
    return render(request, 'informes/cierre.html', dict(
        selected=selected, monthly=monthly, desde=start, hasta=end, totals=totals,
        payments=payments, pending=pending, cancelled=cancelled, sales=sales,
        paid_count=paid.count(), generated=timezone.localtime(),
    ))


@login_required
@never_cache
def propietario(request, historial_pk):
    history = get_object_or_404(HistorialMedico.objects.select_related('paciente__propietario', 'paciente__especie', 'paciente__raza', 'veterinario'), pk=historial_pk)
    return render(request, 'informes/propietario.html', {'h': history, 'p': history.paciente})


@login_required
@never_cache
def consultas(request):
    query = request.GET.get('q', '').strip()
    histories = HistorialMedico.objects.select_related('paciente__propietario').order_by('-fecha')
    if query:
        histories = histories.filter(Q(paciente__nombre__icontains=query) | Q(paciente__propietario__nombre__icontains=query) | Q(paciente__propietario__apellido__icontains=query))
    from django.core.paginator import Paginator
    return render(request, 'informes/consultas.html', {'page': Paginator(histories, 30).get_page(request.GET.get('pagina')), 'query': query})


def bounded_int(request, key, default):
    try:
        return min(365, max(0, int(request.GET.get(key, default))))
    except (ValueError, TypeError):
        return default


@admin_report
def stock(request):
    today = timezone.localdate()
    start = today - timedelta(days=90)
    lead = bounded_int(request, 'reposicion', 7)
    reserve = bounded_int(request, 'reserva', 7)
    outgoing = dict(MovimientoInventario.objects.filter(
        tipo='salida', cantidad__gt=0, fecha__date__gte=start, fecha__date__lt=today,
    ).values('producto_id').annotate(units=Sum('cantidad')).values_list('producto_id', 'units'))
    products = list(Producto.objects.filter(activo=True).exclude(tipo='servicio').select_related('categoria', 'proveedor'))
    for p in products:
        p.units90 = outgoing.get(p.pk, 0)
        # Avoid treating days before product registration as observed zero demand.
        p.days = max(1, min(90, (today - timezone.localdate(p.fecha_registro)).days))
        p.daily = Decimal(p.units90) / p.days
        p.suggested = int((p.daily * (lead + reserve)).to_integral_value(rounding=ROUND_CEILING)) if p.units90 else None
        p.order = max(0, max(p.stock_minimo, p.suggested or 0) - p.stock)
        p.value = p.stock * p.precio_compra
    if request.GET.get('exportar') == 'csv':
        rows = [['Codigo', 'Producto', 'Stock', 'Minimo configurado', 'Salidas periodo', 'Dias observados', 'Promedio diario', 'Minimo sugerido', 'Reposicion sugerida', 'Valor costo Q']]
        rows += [[p.codigo, p.nombre, p.stock, p.stock_minimo, p.units90, p.days, round(p.daily, 2), p.suggested if p.suggested is not None else 'Sin historial', p.order, p.value] for p in products]
        return csv_report(f'inventario-{today}', rows)
    return render(request, 'informes/stock.html', dict(products=products, lead=lead, reserve=reserve, start=start, today=today,
        value=sum((p.value for p in products), Decimal('0')), alerts=sum(p.stock <= p.stock_minimo for p in products)))
