from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import JsonResponse

def healthz(request):
    return JsonResponse({'status': 'ok'})

@login_required
def dashboard(request):
    from pacientes.models import Paciente
    from citas.models import Cita
    from productos.models import Producto
    from ventas.models import Venta
    from django.db.models import Sum, F

    hoy = timezone.now().date()
    total_pacientes = Paciente.objects.filter(estado='activo').count()
    citas_hoy = Cita.objects.filter(fecha_hora__date=hoy).count()
    ventas_hoy = Venta.objects.filter(fecha__date=hoy, estado='pagada').aggregate(t=Sum('total'))['t'] or 0
    productos_stock_bajo = Producto.objects.filter(activo=True, stock__lte=F('stock_minimo')).exclude(tipo='servicio')[:5]
    proximas_citas = Cita.objects.filter(
        fecha_hora__gte=timezone.now(), estado__in=['pendiente','confirmada']
    ).select_related('paciente','veterinario').order_by('fecha_hora')[:5]

    return render(request, 'base/dashboard.html', {
        'total_pacientes': total_pacientes,
        'citas_hoy': citas_hoy,
        'ventas_hoy': ventas_hoy,
        'stock_bajo': productos_stock_bajo.count(),
        'productos_stock_bajo': productos_stock_bajo,
        'proximas_citas': proximas_citas,
    })

urlpatterns = [
    path('healthz/', healthz, name='healthz'),
    path('admin/', admin.site.urls),
    path('', dashboard, name='home'),
    path('auth/', include('django.contrib.auth.urls')),
    path('productos/', include('productos.urls')),
    path('clientes/', include('clientes.urls')),
    path('pacientes/', include('pacientes.urls')),
    path('proveedores/', include('proveedores.urls')),
    path('empleados/', include('empleados.urls')),
    path('citas/', include('citas.urls')),
    path('caja/', include('caja.urls')),
    path('ventas/', include('ventas.urls')),
    path('informes/', include('informes.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
