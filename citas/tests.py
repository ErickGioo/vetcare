from datetime import datetime, timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone

from clientes.models import Cliente
from pacientes.models import Paciente
from .models import Cita


@override_settings(SECURE_SSL_REDIRECT=False, ALLOWED_HOSTS=['testserver'])
class TelevisionTests(TestCase):
    def setUp(self):
        from django.contrib.auth.models import Permission
        viewer = User.objects.create_user(username='tv')
        viewer.user_permissions.add(Permission.objects.get(codename='view_cita'))
        self.client.force_login(viewer)
        owner = Cliente.objects.create(nombre='Private owner', apellido='Hidden')
        self.pet = Paciente.objects.create(nombre='Luna', propietario=owner, sexo='H')
        self.now = timezone.make_aware(datetime(2026, 10, 21, 12))

    def appointment(self, state, when=None):
        return Cita.objects.create(paciente=self.pet, estado=state,
                                   fecha_hora=when or self.now, motivo='Private clinical note')

    def get_board(self, query=''):
        with patch('citas.tv.timezone.localtime', return_value=self.now):
            return self.client.get('/citas/tv/' + query)

    def test_requires_login(self):
        self.client.logout()
        self.assertEqual(self.get_board().status_code, 302)

    def test_local_day_boundaries_and_grouping(self):
        start = self.now.replace(hour=0)
        for state in ('pendiente', 'confirmada', 'en_curso', 'completada', 'cancelada', 'no_asistio'):
            self.appointment(state, start)
        self.appointment('pendiente', start - timedelta(seconds=1))
        self.appointment('pendiente', start + timedelta(days=1))
        response = self.get_board()
        self.assertEqual(response.context['total'], 6)
        self.assertEqual([g['total'] for g in response.context['groups']], [2, 1, 3])
        self.assertEqual(response.context['completed'], 1)
        self.assertEqual(response.context['progress'], 50)
        self.assertNotContains(response, 'Private owner')
        self.assertNotContains(response, 'Private clinical note')
        self.assertIn('no-store', response['Cache-Control'])

    def test_rotation_and_live_status_changes(self):
        appointments = [self.appointment('pendiente') for _ in range(7)]
        response = self.get_board('?pagina=3')
        self.assertEqual(response.context['pages'], 3)
        self.assertEqual(len(response.context['groups'][0]['items']), 1)
        appointments[0].estado = 'en_curso'
        appointments[0].save()
        response = self.get_board('?pagina=invalid')
        self.assertEqual(response.context['page'], 1)
        self.assertEqual(response.context['groups'][1]['total'], 1)

    def test_empty_day(self):
        self.assertContains(self.get_board(), 'No hay citas agendadas para hoy.')

    def test_grooming_appointment_in_tv_tracking(self):
        appointment = self.appointment('confirmada')
        appointment.tipo = 'peluqueria'
        appointment.save()
        self.assertContains(self.get_board(), 'Grooming / peluquería')
        from .views import CitaForm
        form = CitaForm(dict(paciente=self.pet.pk, tipo='bano', fecha_hora=self.now.isoformat(), duracion_minutos=45, estado='pendiente', motivo='Baño de mantenimiento'))
        self.assertTrue(form.is_valid(), form.errors)

    def test_review_edit_form_preserves_date_and_time(self):
        appointment = self.appointment('pendiente')
        from .views import CitaForm
        form = CitaForm(instance=appointment)
        expected = timezone.localtime(appointment.fecha_hora).strftime('%Y-%m-%dT%H:%M')
        self.assertIn(f'value="{expected}"', str(form['fecha_hora']))
