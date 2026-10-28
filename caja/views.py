from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect
from django.utils import timezone

from informes.operacion import admin_report
from .forms import AperturaForm, CierreForm
from .models import CajaDiaria, CobroCaja
from .operaciones import abrir, cerrar, totales, METODOS


@admin_report
def panel(request):
    try:
        selected = date.fromisoformat(request.GET.get('fecha', str(timezone.localdate())))
    except ValueError:
        selected = timezone.localdate()
    caja = CajaDiaria.objects.filter(fecha=selected).select_related('abierta_por', 'cerrada_por').first()
    apertura = AperturaForm(request.POST if request.method == 'POST' and request.POST.get('accion') == 'abrir' else None)
    cierre = CierreForm(request.POST if request.method == 'POST' and request.POST.get('accion') == 'cerrar' else None)
    if request.method == 'POST':
        try:
            if request.POST.get('accion') == 'abrir' and apertura.is_valid():
                nueva = abrir(request.user, apertura.cleaned_data['inicial'])
                messages.success(request, 'Caja abierta. El efectivo inicial no se cuenta como venta.')
                return redirect('/caja/?fecha=' + str(nueva.fecha))
            elif request.POST.get('accion') == 'cerrar' and cierre.is_valid() and caja:
                cerrar(caja.pk, request.user, cierre.cleaned_data, cierre.cleaned_data['observaciones'])
                messages.success(request, 'Caja cerrada y cuadre guardado.')
                return redirect('/caja/?fecha=' + str(caja.fecha))
        except ValidationError as error:
            messages.error(request, ' '.join(error.messages))
    rows = []
    sales = Decimal('0')
    if caja:
        amounts = totales(caja)
        sales = sum(amounts.values())
        labels = {'efectivo':'Efectivo', 'transferencia':'Transferencias', 'tarjeta':'Tarjeta'}
        for method in METODOS:
            expected = Decimal(caja.esperado[method]) if caja.cerrada_en else amounts[method] + (caja.inicial if method == 'efectivo' else 0)
            counted = Decimal(caja.contado[method]) if caja.cerrada_en else None
            rows.append({'nombre':labels[method], 'ventas':amounts[method], 'esperado':expected, 'contado':counted,
                'diferencia':counted - expected if counted is not None else None})
    return render(request, 'caja/panel.html', {
        'caja':caja, 'fecha':selected, 'hoy':timezone.localdate(), 'apertura':apertura, 'cierre':cierre,
        'filas':rows, 'total_ventas':sales, 'historial':CajaDiaria.objects.all()[:31],
        'sin_caja':CobroCaja.objects.filter(caja__isnull=True, fecha__date=selected).select_related('venta'),
    })


@admin_report
def accesos(request):
    from django.core.paginator import Paginator
    from .models import AccesoSistema
    try:
        selected = date.fromisoformat(request.GET.get('fecha', str(timezone.localdate())))
    except ValueError:
        selected = timezone.localdate()
    records = AccesoSistema.objects.filter(fecha__date=selected).select_related('usuario')
    return render(request, 'caja/accesos.html', {'fecha':selected, 'pagina':Paginator(records, 50).get_page(request.GET.get('page'))})
