import json
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Sum, Value
from django.db.models.functions import Coalesce, TruncMonth
from django.shortcuts import render
from django.utils import timezone

from citas.models import Cita
from productos.models import MovimientoInventario, Producto
from ventas.models import DetalleVenta, Venta


MONEY_FIELD = DecimalField(max_digits=14, decimal_places=2)


def _month_start(value):
    return value.replace(day=1)


def _shift_month(value, delta):
    month_number = value.month - 1 + delta
    year = value.year + month_number // 12
    month = month_number % 12 + 1
    return date(year, month, 1)


def _date_range(request):
    today = timezone.localdate()
    default_start = _month_start(today)
    try:
        start = datetime.strptime(request.GET.get('desde', ''), '%Y-%m-%d').date()
    except ValueError:
        start = default_start
    try:
        end = datetime.strptime(request.GET.get('hasta', ''), '%Y-%m-%d').date()
    except ValueError:
        end = today
    if start > end:
        start, end = end, start
    return start, end


def _paid_items(start, end):
    return DetalleVenta.objects.filter(
        venta__estado='pagada',
        venta__fecha__date__range=(start, end),
    ).select_related('producto', 'venta')


def _item_totals(queryset):
    neto = ExpressionWrapper(
        F('precio_unitario') * F('cantidad') * (Value(Decimal('1.00')) - F('descuento_pct') / Value(Decimal('100.00'))),
        output_field=MONEY_FIELD,
    )
    costo = ExpressionWrapper(F('costo_unitario') * F('cantidad'), output_field=MONEY_FIELD)
    ganancia = ExpressionWrapper(neto - costo, output_field=MONEY_FIELD)
    return queryset.aggregate(
        ingresos=Coalesce(Sum(neto), Value(Decimal('0.00'), output_field=MONEY_FIELD)),
        costos=Coalesce(Sum(costo), Value(Decimal('0.00'), output_field=MONEY_FIELD)),
        ganancia=Coalesce(Sum(ganancia), Value(Decimal('0.00'), output_field=MONEY_FIELD)),
        unidades=Coalesce(Sum('cantidad'), Value(0)),
    )


def _month_series():
    current = _month_start(timezone.localdate())
    return [_shift_month(current, -offset) for offset in range(5, -1, -1)]


def _monthly_chart_data():
    months = _month_series()
    first = months[0]
    sales = (
        Venta.objects.filter(estado='pagada', fecha__date__gte=first)
        .annotate(periodo=TruncMonth('fecha'))
        .values('periodo')
        .annotate(total=Sum('total'))
        .order_by('periodo')
    )
    visits = (
        Cita.objects.filter(fecha_hora__date__gte=first, estado='completada')
        .annotate(periodo=TruncMonth('fecha_hora'))
        .values('periodo')
        .annotate(total=Count('id'))
        .order_by('periodo')
    )
    sales_by_month = {row['periodo'].date().replace(day=1): float(row['total'] or 0) for row in sales}
    visits_by_month = {row['periodo'].date().replace(day=1): row['total'] for row in visits}
    return {
        'labels': [item.strftime('%b %Y') for item in months],
        'ventas': [sales_by_month.get(item, 0) for item in months],
        'visitas': [visits_by_month.get(item, 0) for item in months],
    }


@login_required
def resumen(request):
    start, end = _date_range(request)
    paid_sales = Venta.objects.filter(estado='pagada', fecha__date__range=(start, end))
    totals = _item_totals(_paid_items(start, end))
    totals['ingresos'] = paid_sales.aggregate(total=Sum('total'))['total'] or Decimal('0.00')
    totals['ganancia'] = totals['ingresos'] - totals['costos']
    citas = Cita.objects.filter(fecha_hora__date__range=(start, end))
    top_products = (
        _paid_items(start, end).values('producto__nombre', 'producto__codigo')
        .annotate(unidades=Sum('cantidad'))
        .order_by('-unidades')[:5]
    )
    chart_data = _monthly_chart_data()
    return render(request, 'informes/resumen.html', {
        'desde': start,
        'hasta': end,
        'ventas_pagadas': paid_sales.count(),
        'visitas': citas.filter(estado='completada').count(),
        'citas_programadas': citas.exclude(estado__in=['cancelada', 'no_asistio']).count(),
        'ingresos': totals['ingresos'],
        'ganancia': totals['ganancia'],
        'margen': (totals['ganancia'] / totals['ingresos'] * 100) if totals['ingresos'] else 0,
        'stock_bajo': Producto.objects.filter(activo=True, stock__lte=F('stock_minimo')).exclude(tipo='servicio').count(),
        'top_products': top_products,
        'chart_data': json.dumps(chart_data),
    })


@login_required
def ventas(request):
    start, end = _date_range(request)
    items = _paid_items(start, end)
    totals = _item_totals(items)
    totals['ingresos'] = Venta.objects.filter(estado='pagada', fecha__date__range=(start, end)).aggregate(total=Sum('total'))['total'] or Decimal('0.00')
    totals['ganancia'] = totals['ingresos'] - totals['costos']
    productos = (
        items.values('producto__codigo', 'producto__nombre')
        .annotate(
            unidades=Sum('cantidad'),
            ingresos=Sum(ExpressionWrapper(
                F('precio_unitario') * F('cantidad') * (Value(Decimal('1.00')) - F('descuento_pct') / Value(Decimal('100.00'))),
                output_field=MONEY_FIELD,
            )),
            costos=Sum(ExpressionWrapper(F('costo_unitario') * F('cantidad'), output_field=MONEY_FIELD)),
        )
        .order_by('-ingresos')
    )
    for product in productos:
        product['ganancia'] = (product['ingresos'] or 0) - (product['costos'] or 0)

    ventas_pagadas = Venta.objects.filter(estado='pagada', fecha__date__range=(start, end)).select_related('cliente', 'empleado')
    return render(request, 'informes/ventas.html', {
        'desde': start, 'hasta': end, 'totals': totals,
        'ventas_pagadas': ventas_pagadas, 'productos': productos,
    })


@login_required
def inventario(request):
    productos = Producto.objects.select_related('categoria', 'proveedor').filter(activo=True)
    inventory = list(productos)
    for product in inventory:
        product.valor_costo = product.stock * product.precio_compra
        product.valor_venta = product.stock * product.precio_venta

    resumen_inventario = {
        'productos': len(inventory),
        'unidades': sum(item.stock for item in inventory),
        'valor_costo': sum((item.valor_costo for item in inventory), Decimal('0.00')),
        'valor_venta': sum((item.valor_venta for item in inventory), Decimal('0.00')),
        'stock_bajo': sum(1 for item in inventory if item.stock <= item.stock_minimo),
        'sin_stock': sum(1 for item in inventory if item.stock <= 0),
    }
    movimientos = MovimientoInventario.objects.select_related('producto', 'usuario').all()[:12]
    return render(request, 'informes/inventario.html', {
        'productos': inventory,
        'resumen': resumen_inventario,
        'movimientos': movimientos,
    })


@login_required
def pantalla(request):
    now = timezone.localtime()
    today = now.date()
    citas_hoy = Cita.objects.filter(fecha_hora__date=today).exclude(estado__in=['cancelada', 'no_asistio'])
    proximas = citas_hoy.filter(fecha_hora__gte=now).select_related('paciente', 'veterinario').order_by('fecha_hora')[:6]
    ventas_hoy = Venta.objects.filter(estado='pagada', fecha__date=today).aggregate(total=Sum('total'))['total'] or Decimal('0.00')
    return render(request, 'informes/pantalla.html', {
        'ahora': now,
        'citas_hoy': citas_hoy.count(),
        'atendidas': citas_hoy.filter(estado='completada').count(),
        'ventas_hoy': ventas_hoy,
        'stock_bajo': Producto.objects.filter(activo=True, stock__lte=F('stock_minimo')).exclude(tipo='servicio').count(),
        'proximas': proximas,
    })
