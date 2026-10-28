from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone

from clientes.models import Cliente
from pacientes.models import Paciente, HistorialMedico
from productos.models import Producto, MovimientoInventario
from ventas.models import Venta, DetalleVenta


@override_settings(SECURE_SSL_REDIRECT=False, ALLOWED_HOSTS=['testserver'])
class ReportTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user('admin', is_staff=True)
        from django.contrib.auth.models import Permission
        self.staff.user_permissions.set(Permission.objects.all())
        self.client.force_login(self.staff)
        self.owner = Cliente.objects.create(nombre='Ana', apellido='Lopez')
        self.pet = Paciente.objects.create(nombre='Luna', propietario=self.owner, sexo='H')
        self.product = Producto.objects.create(codigo='P1', nombre='Alimento', stock=100, precio_compra=Decimal('10'), precio_venta=Decimal('20'))

    def sale(self, number, state='pagada'):
        sale = Venta.objects.create(numero=number, cliente=self.owner, estado=state)
        DetalleVenta.objects.create(venta=sale, producto=self.product, cantidad=2, precio_unitario=Decimal('20'), descuento_pct=Decimal('10'))
        sale.calcular_totales()
        return sale

    def test_paid_profit_and_historical_cost(self):
        self.sale('V1')
        self.sale('V2', 'pendiente')
        self.sale('V3', 'anulada')
        self.product.precio_compra = Decimal('15')
        self.product.save()
        response = self.client.get('/informes/cierres/')
        self.assertEqual(response.context['totals']['ingresos'], Decimal('36'))
        self.assertEqual(response.context['totals']['costos'], Decimal('20'))
        self.assertEqual(response.context['totals']['ganancia'], Decimal('16'))
        self.assertEqual(response.context['paid_count'], 1)
        self.assertEqual(sum(p['total'] for p in response.context['payments']), Decimal('36'))

    def test_month_boundary(self):
        sale = self.sale('OLD')
        last_month = timezone.localtime().replace(day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(seconds=1)
        Venta.objects.filter(pk=sale.pk).update(fecha=last_month)
        self.assertEqual(self.client.get('/informes/cierres/?periodo=mensual').context['paid_count'], 0)
        self.assertEqual(self.client.get('/informes/cierres/', {'periodo':'mensual', 'fecha':last_month.date().isoformat()}).context['paid_count'], 1)

    def test_staff_access_and_csv(self):
        self.sale('=formula')
        response = self.client.get('/informes/cierres/?exportar=csv')
        self.assertContains(response, "'=formula")
        self.client.force_login(User.objects.create_user('ordinary'))
        self.assertEqual(self.client.get('/informes/cierres/').status_code, 403)
        self.assertEqual(self.client.get('/informes/inventario/').status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get('/informes/consultas/').status_code, 302)

    def test_stock_suggestion_and_no_history(self):
        Producto.objects.filter(pk=self.product.pk).update(fecha_registro=timezone.now()-timedelta(days=100))
        m = MovimientoInventario.objects.create(producto=self.product, tipo='salida', cantidad=90, stock_anterior=190, stock_posterior=100, motivo='Consumo')
        MovimientoInventario.objects.filter(pk=m.pk).update(fecha=timezone.now()-timedelta(days=5))
        Producto.objects.create(codigo='S', nombre='Consulta', tipo='servicio', precio_venta=50)
        new = Producto.objects.create(codigo='NEW', nombre='Sin historia', precio_venta=20)
        response = self.client.get('/informes/inventario/?reposicion=7&reserva=7')
        products = {p.pk:p for p in response.context['products']}
        self.assertEqual(products[self.product.pk].suggested, 14)
        self.assertIsNone(products[new.pk].suggested)
        self.assertEqual(len(products), 2)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_minimo, 5)

    def test_owner_report_excludes_private_notes(self):
        history = HistorialMedico.objects.create(paciente=self.pet, motivo='Control', diagnostico_definitivo='Estable', tratamiento='Reposo', observaciones='INTERNO_SECRETO', anamnesis='INTERNO_ANAMNESIS')
        response = self.client.get(f'/informes/consulta/{history.pk}/dueno/')
        self.assertContains(response, 'Estable')
        self.assertContains(response, 'Informe provisional')
        self.assertNotContains(response, 'INTERNO_SECRETO')
        self.assertNotContains(response, 'INTERNO_ANAMNESIS')

    def test_empty_reports(self):
        for path in ['/informes/', '/informes/ventas/', '/informes/cierres/', '/informes/inventario/', '/informes/consultas/']:
            self.assertEqual(self.client.get(path).status_code, 200)

    def test_service_counts_completed_appointments_without_sales(self):
        from datetime import datetime
        from citas.models import Cita
        for day, kind, state in [(1,'peluqueria','completada'), (2,'peluqueria','completada'),
                                 (2,'consulta','completada'), (2,'bano','cancelada'),
                                 (2,'peluqueria','pendiente'), (8,'bano','completada')]:
            Cita.objects.create(paciente=self.pet, tipo=kind, estado=state, motivo='Atención',
                fecha_hora=timezone.make_aware(datetime(2026, 6, day, 10)))
        HistorialMedico.objects.create(paciente=self.pet, motivo='Sin duplicar', diagnostico_definitivo='Sano', tratamiento='Reposo', estado='cerrada')
        for period, expected in [('diario',2), ('semanal',3), ('mensual',4)]:
            response = self.client.get('/informes/servicios/', {'fecha':'2026-06-02','periodo':period})
            self.assertEqual(response.context['total'], expected)
        self.assertFalse(Venta.objects.exists())
        self.client.force_login(User.objects.create_user('no_staff'))
        self.assertEqual(self.client.get('/informes/servicios/').status_code,403)
