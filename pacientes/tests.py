from datetime import timedelta, time
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.utils import timezone

from clientes.models import Cliente
from citas.models import Cita
from productos.models import Producto, MovimientoInventario
from ventas.models import Venta
from ventas.operaciones import cambiar_cantidad
from .models import Paciente, HistorialMedico, Especie, Raza
from .forms import PacienteForm
from .integracion import facturar_consulta, sincronizar_revision


@override_settings(SECURE_SSL_REDIRECT=False, ALLOWED_HOSTS=['testserver'])
class ClinicIntegrationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('vet', is_staff=True)
        from django.contrib.auth.models import Permission
        self.user.user_permissions.set(Permission.objects.all())
        self.client.force_login(self.user)
        self.owner = Cliente.objects.create(nombre='Ana', apellido='Test')
        self.dog = Especie.objects.create(nombre='Perro')
        self.cat = Especie.objects.create(nombre='Gato')
        self.lab = Raza.objects.create(nombre='Labrador', especie=self.dog)
        self.siam = Raza.objects.create(nombre='Siamés', especie=self.cat)
        self.pet = Paciente.objects.create(nombre='Luna', propietario=self.owner, especie=self.dog, raza=self.lab, sexo='H')
        self.service = Producto.objects.create(codigo='CONS', nombre='Consulta general', tipo='servicio', precio_venta=150, precio_compra=30, stock=0)
        self.history = HistorialMedico.objects.create(paciente=self.pet, veterinario=self.user, motivo='Revisión', diagnostico_definitivo='Estable', tratamiento='Reposo')

    def test_breed_filter_and_server_validation(self):
        response = self.client.get('/pacientes/razas/', {'especie':self.dog.pk, 'q':'La'})
        self.assertEqual([r['nombre'] for r in response.json()['razas']], ['Labrador'])
        response = self.client.get('/pacientes/razas/', {'especie':self.cat.pk, 'q':'La'})
        self.assertEqual(response.json()['razas'], [])
        data = dict(propietario=self.owner.pk,nombre='Otro',especie=self.dog.pk,raza=self.siam.pk,sexo='H',estado='activo')
        form = PacienteForm(data)
        self.assertFalse(form.is_valid())
        self.assertIn('raza', form.errors)
        self.assertEqual(PacienteForm(instance=self.pet).fields['raza'].queryset.count(), 1)

    def test_one_sale_per_consultation_and_revenue_after_payment(self):
        first = facturar_consulta(self.history.pk, self.service.pk, self.user)
        second = facturar_consulta(self.history.pk, self.service.pk, self.user)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(Venta.objects.count(), 1)
        self.assertEqual(first.total, Decimal('150'))
        self.assertFalse(MovimientoInventario.objects.exists())
        self.assertEqual(self.client.get('/informes/cierres/').context['totals']['ingresos'], 0)
        self.client.post(f'/ventas/{first.pk}/pagar/')
        totals = self.client.get('/informes/cierres/').context['totals']
        self.assertEqual(totals['ingresos'], Decimal('150'))
        self.assertEqual(totals['ganancia'], Decimal('120'))
        with self.assertRaises(ValidationError):
            cambiar_cantidad(first.pk, first.items.first().pk, 0, self.user)

    def test_review_creates_and_updates_without_duplicates(self):
        self.history.proxima_cita = timezone.localdate() + timedelta(days=7)
        self.history.proxima_hora = time(10,30)
        self.history.save()
        first = sincronizar_revision(self.history.pk)
        self.assertEqual(first.tipo, 'control')
        self.assertEqual(first.estado, 'pendiente')
        self.history.proxima_cita += timedelta(days=1)
        self.history.save(update_fields=['proxima_cita'])
        second = sincronizar_revision(self.history.pk)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(Cita.objects.count(), 1)
        self.assertEqual(timezone.localtime(second.fecha_hora).date(), self.history.proxima_cita)

    def test_create_consultation_requires_service_and_schedules_review(self):
        future = timezone.localdate() + timedelta(days=5)
        data = dict(motivo='Control', diagnostico_definitivo='Sano', tratamiento='Reposo',estado='abierta',proxima_cita=future.isoformat(),proxima_hora='09:30',servicio=self.service.pk)
        response = self.client.post(f'/pacientes/{self.pet.pk}/historial/nuevo/', data)
        self.assertEqual(response.status_code, 302)
        history = HistorialMedico.objects.latest('pk')
        self.assertIsNotNone(history.venta_id)
        self.assertIsNotNone(history.cita_revision_id)
        self.assertEqual(timezone.localtime(history.cita_revision.fecha_hora).time(), time(9,30))
        data.pop('servicio')
        self.assertEqual(self.client.post(f'/pacientes/{self.pet.pk}/historial/nuevo/',data).status_code, 200)
        self.assertEqual(HistorialMedico.objects.count(), 2)

    def test_owner_report_breed_and_letterhead(self):
        response = self.client.get(f'/informes/consulta/{self.history.pk}/dueno/')
        self.assertContains(response, 'Labrador')
        self.assertContains(response, 'Emblema Vetcare')

    def test_missing_revision_time_is_rejected(self):
        data = dict(motivo='Control',diagnostico_definitivo='Sano',tratamiento='Reposo',estado='abierta',proxima_cita=(timezone.localdate()+timedelta(days=5)).isoformat(),servicio=self.service.pk)
        response = self.client.post(f'/pacientes/{self.pet.pk}/historial/nuevo/',data)
        self.assertContains(response, 'Indica la hora')
        self.assertEqual(Venta.objects.count(), 0)

    def test_postconsultation_schedules_and_keeps_existing_bill(self):
        sale = facturar_consulta(self.history.pk, self.service.pk, self.user)
        data = dict(diagnostico_definitivo='Sano', estado='seguimiento', proxima_cita=(timezone.localdate()+timedelta(days=4)).isoformat(), proxima_hora='11:00',motivo_proxima_cita='Revisión')
        url=f'/pacientes/{self.pet.pk}/historial/{self.history.pk}/post-consulta/'
        self.assertEqual(self.client.post(url,data).status_code,302)
        self.assertEqual(self.client.post(url,data).status_code,302)
        self.history.refresh_from_db()
        self.assertEqual(self.history.venta_id,sale.pk)
        self.assertEqual(Cita.objects.count(),1)
        self.assertEqual(Venta.objects.count(),1)
        with self.assertRaises(ValidationError):
            cambiar_cantidad(sale.pk,self.history.detalle_servicio_id,0,self.user)

    def test_quick_service_creation_and_selection(self):
        response=self.client.post('/pacientes/servicios/nuevo/', {'nombre':'Revisión nueva','precio':'125.50','costo':'20'})
        self.assertEqual(response.status_code,200)
        product=Producto.objects.get(pk=response.json()['id'])
        self.assertEqual(product.tipo,'servicio')
        self.assertEqual(product.stock,0)
        self.assertEqual(product.precio_venta,Decimal('125.50'))
        again=self.client.post('/pacientes/servicios/nuevo/', {'nombre':'Revisión nueva','precio':'125.50','costo':'20'})
        self.assertEqual(response.json()['id'],again.json()['id'])
        self.assertFalse(MovimientoInventario.objects.exists())

    def test_quick_service_validation_and_permissions(self):
        for price in ('0','-1','abc','12.345'):
            self.assertEqual(self.client.post('/pacientes/servicios/nuevo/',{'nombre':'Inválido','precio':price}).status_code,400)
        self.assertFalse(Producto.objects.filter(nombre='Inválido').exists())
        self.client.force_login(User.objects.create_user('normal'))
        self.assertEqual(self.client.post('/pacientes/servicios/nuevo/',{'nombre':'No permitido','precio':'10'}).status_code,403)

    def test_quick_service_requires_csrf_and_preserves_invalid_consultation(self):
        from django.test import Client
        client=Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post('/pacientes/servicios/nuevo/',{'nombre':'Sin CSRF','precio':'10'}).status_code,403)
        response=self.client.post(f'/pacientes/{self.pet.pk}/historial/nuevo/',{'motivo':'Conservar este motivo','estado':'abierta','servicio':self.service.pk})
        self.assertContains(response,'Conservar este motivo')
        self.assertNotContains(response,'Guardar servicio y seleccionarlo')
        self.assertContains(response,'Selecciona un servicio existente')

    def test_consultations_reuse_catalog_without_creating_products(self):
        count = Producto.objects.count()
        for _ in range(2):
            response = self.client.post(f'/pacientes/{self.pet.pk}/historial/nuevo/', dict(
                motivo='Control', diagnostico_definitivo='Sano', tratamiento='Reposo',
                estado='cerrada', servicio=self.service.pk))
            self.assertEqual(response.status_code, 302)
        self.assertEqual(Producto.objects.count(), count)
        self.assertEqual(Venta.objects.count(), 2)
        self.assertFalse(MovimientoInventario.objects.exists())
        sale = Venta.objects.latest('pk')
        self.assertContains(self.client.get('/ventas/?estado=pendiente'), sale.numero)
        self.assertNotContains(self.client.get('/ventas/?estado=pagada'), sale.numero)
        self.assertEqual(self.client.get(f'/ventas/{sale.pk}/pagar/').status_code, 405)
        self.client.post(f'/ventas/{sale.pk}/pagar/')
        self.assertContains(self.client.get('/ventas/?estado=pagada'), sale.numero)
        self.assertNotContains(self.client.get('/ventas/?estado=pendiente'), sale.numero)
        self.assertEqual(Producto.objects.count(), count)
