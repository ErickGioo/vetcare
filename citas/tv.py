from datetime import datetime, time, timedelta
from math import ceil

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.cache import never_cache

from .models import Cita


@login_required
@never_cache
def television(request):
    now = timezone.localtime()
    start = timezone.make_aware(datetime.combine(now.date(), time.min))
    end = timezone.make_aware(datetime.combine(now.date() + timedelta(days=1), time.min))
    appointments = list(Cita.objects.filter(fecha_hora__gte=start, fecha_hora__lt=end)
                        .select_related('paciente', 'paciente__especie')
                        .order_by('fecha_hora', 'pk'))
    definitions = [
        ('scheduled', 'Programadas', ('pendiente', 'confirmada'), '01'),
        ('active', 'En atención', ('en_curso',), '02'),
        ('finished', 'Finalizadas', ('completada', 'cancelada', 'no_asistio'), '03'),
    ]
    groups = []
    for key, title, states, number in definitions:
        items = [c for c in appointments if c.estado in states]
        groups.append({'key': key, 'title': title, 'number': number,
                       'total': len(items), 'items': items})
    pages = max(1, max(ceil(group['total'] / 3) for group in groups))
    try:
        page = max(1, int(request.GET.get('pagina', '1')))
    except ValueError:
        page = 1
    page = (page - 1) % pages + 1
    for group in groups:
        # Short columns keep showing their cards while longer columns rotate.
        group_page = (page - 1) % max(1, ceil(group['total'] / 3))
        group['items'] = group['items'][group_page * 3:(group_page + 1) * 3]
    completed = sum(c.estado == 'completada' for c in appointments)
    closed = groups[2]['total']
    return render(request, 'citas/television.html', {
        'groups': groups, 'today': now, 'updated': now.isoformat(),
        'total': len(appointments), 'completed': completed,
        'cancelled': sum(c.estado == 'cancelada' for c in appointments),
        'absent': sum(c.estado == 'no_asistio' for c in appointments),
        'progress': round(closed / len(appointments) * 100) if appointments else 0,
        'page': page, 'pages': pages,
    })
