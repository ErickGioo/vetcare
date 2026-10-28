from datetime import timedelta, datetime
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.utils import timezone

from clientes.models import Cliente
from productos.models import Producto
from ventas.models import Venta, DetalleVenta, PagoNeonet
from .models import CajaDiaria, CobroCaja
from .operaciones import abrir, cerrar, totales


@override_settings(SECURE_SSL_REDIRECT=False, ALLOWED_HOSTS=['testserver'])
class CajaTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('admin', is_staff=True, is_superuser=True)
        self.client.force_login(self.user)
        self.owner = Cliente.objects.create(nombre='Ana', apellido='Test')
        self.service = Producto.objects.create(codigo='S', nombre='Consulta', tipo='servicio', precio_venta=100)

    def venta(self, method='efectivo'):
        sale = Venta.objects.create(numero=uuid4().hex[:15], cliente=self.owner, tipo_pago=method)
        DetalleVenta.objects.create(venta=sale, producto=self.service, cantidad=1, precio_unitario=100)
        sale.calcular_totales()
        return sale

    def pagar(self, sale):
        return self.client.post(f'/ventas/{sale.pk}/pagar/')

    def test_open_pay_close_and_immutable_snapshot(self):
        caja = abrir(self.user, Decimal('50'))
        cash = self.venta()
        transfer = self.venta('transferencia')
        Venta.objects.filter(pk=cash.pk).update(fecha=timezone.now()-timedelta(days=7))
        self.pagar(cash)
        self.pagar(cash)
        self.pagar(transfer)
        self.assertEqual(CobroCaja.objects.count(), 2)
        self.assertEqual(totales(caja)['efectivo'], 100)
        cerrar(caja.pk, self.user, {'efectivo':Decimal('145'), 'transferencia':Decimal('100'), 'tarjeta':Decimal('0')}, 'Faltante Q5')
        caja.refresh_from_db()
        self.assertEqual(Decimal(caja.esperado['efectivo']), 150)
        self.assertEqual(Decimal(caja.contado['efectivo']), 145)
        with self.assertRaises(ValidationError):
            cerrar(caja.pk,self.user,{},'')
        with self.assertRaises(ValidationError):
            abrir(self.user, Decimal('0'))
        late = self.venta()
        self.pagar(late)
        self.assertIsNone(CobroCaja.objects.get(venta=late).caja_id)
        response = self.client.get('/caja/')
        self.assertContains(response, 'Cobros fuera de caja')
        self.assertContains(response, 'Faltante Q5')
        self.assertEqual(response.context['filas'][0]['diferencia'], -5)
        self.assertEqual(response.context['total_ventas'], 200)

    def test_before_open_captures_today_only(self):
        sale = self.venta()
        self.pagar(sale)
        old = self.venta()
        self.pagar(old)
        CobroCaja.objects.filter(venta=old).update(fecha=timezone.now()-timedelta(days=2))
        caja = abrir(self.user,Decimal('0'))
        self.assertEqual(caja.cobros.count(),1)
        self.assertEqual(caja.cobros.get().venta_id,sale.pk)

    @patch('ventas.views.verify_response', return_value=True)
    def test_neonet_records_once_and_blocks_close_while_pending(self, verify):
        caja=abrir(self.user,Decimal('0'))
        sale=self.venta('tarjeta')
        pago=PagoNeonet.objects.create(venta=sale,referencia='CARD',transaction_uuid=str(uuid4()))
        with self.assertRaises(ValidationError):
            cerrar(caja.pk,self.user,{'efectivo':0,'transferencia':0,'tarjeta':0},'')
        data={'req_transaction_uuid':pago.transaction_uuid,'decision':'ACCEPT'}
        for _ in range(2):
            self.assertEqual(self.client.post('/ventas/pagos/neonet/respuesta/',data).status_code,200)
        self.assertEqual(caja.cobros.count(),1)
        self.assertEqual(totales(caja)['tarjeta'],100)
        cerrar(caja.pk,self.user,{'efectivo':0,'transferencia':0,'tarjeta':100},'')

    def test_validation_permissions_and_csrf(self):
        self.assertEqual(self.client.get('/caja/').status_code,200)
        for invalid in ('-1','abc','1.001'):
            self.client.post('/caja/',{'accion':'abrir','inicial':invalid})
        self.assertFalse(CajaDiaria.objects.exists())
        from django.test import Client
        csrf=Client(enforce_csrf_checks=True)
        csrf.force_login(self.user)
        self.assertEqual(csrf.post('/caja/',{'accion':'abrir','inicial':'0'}).status_code,403)
        self.client.force_login(User.objects.create_user('normal'))
        self.assertEqual(self.client.get('/caja/').status_code,403)
        self.client.logout()
        self.assertEqual(self.client.get('/caja/').status_code,302)

    def test_previous_open_and_invalid_close(self):
        caja=abrir(self.user,Decimal('10'))
        CajaDiaria.objects.filter(pk=caja.pk).update(fecha=timezone.localdate()-timedelta(days=1))
        with self.assertRaises(ValidationError):
            abrir(self.user,Decimal('0'))
        response=self.client.post('/caja/?fecha='+str(timezone.localdate()-timedelta(days=1)),{'accion':'cerrar','efectivo':'-1','tarjeta':'0','transferencia':'0'})
        self.assertEqual(response.status_code,200)
        caja.refresh_from_db()
        self.assertIsNone(caja.cerrada_en)

    def test_midnight_payment_date_uses_guatemala(self):
        fixed=timezone.make_aware(datetime(2026,10,28,0,30),timezone.get_fixed_timezone(0))
        sale=self.venta()
        with patch('django.utils.timezone.now',return_value=fixed):
            caja=abrir(self.user,Decimal('0'))
            self.pagar(sale)
        self.assertEqual(str(caja.fecha),'2026-10-27')
        self.assertEqual(caja.cobros.count(),1)

    def test_access_audit_date_user_privacy_and_permissions(self):
        from .models import AccesoSistema
        self.client.get('/ventas/?secreto=NO_GUARDAR')
        record=AccesoSistema.objects.latest('pk')
        self.assertEqual(record.usuario_id,self.user.pk)
        self.assertEqual(record.pantalla,'ventas:lista')
        self.assertEqual(timezone.localdate(record.fecha),timezone.localdate())
        self.assertEqual(record.metodo,'GET')
        self.assertEqual(record.resultado,200)
        self.assertNotIn('NO_GUARDAR',record.pantalla)
        self.assertContains(self.client.get('/caja/accesos/'),'ventas:lista')
        self.client.force_login(User.objects.create_user('lector', is_staff=True))
        self.assertEqual(self.client.get('/caja/accesos/').status_code,403)

    def test_reopening_requires_admin_and_preserves_previous_close(self):
        from django.core.exceptions import PermissionDenied
        from .operaciones import solicitar_reapertura, resolver_reapertura
        caja=abrir(self.user,Decimal('50'))
        self.pagar(self.venta())
        cerrar(caja.pk,self.user,{'efectivo':150,'transferencia':0,'tarjeta':0},'Primer cierre')
        staff=User.objects.create_user('cajero',is_staff=True)
        solicitud=solicitar_reapertura(caja.pk,staff,'Corregir el conteo')
        with self.assertRaises(ValidationError):
            solicitar_reapertura(caja.pk,staff,'Duplicada')
        with self.assertRaises(PermissionDenied):
            resolver_reapertura(solicitud.pk,staff,True)
        caja.refresh_from_db()
        self.assertIsNotNone(caja.cerrada_en)
        self.pagar(self.venta('transferencia'))
        resolver_reapertura(solicitud.pk,self.user,True)
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.cierre_anterior['observaciones'],'Primer cierre')
        self.assertEqual(Decimal(solicitud.cierre_anterior['contado']['efectivo']),150)
        self.assertEqual(len(solicitud.cierre_anterior['cobros']),1)
        caja.refresh_from_db()
        self.assertIsNone(caja.cerrada_en)
        self.assertEqual(caja.cobros.count(),2)
        cerrar(caja.pk,self.user,{'efectivo':150,'transferencia':100,'tarjeta':0},'Segundo cierre')
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.cierre_anterior['observaciones'],'Primer cierre')
        with self.assertRaises(ValidationError):
            resolver_reapertura(solicitud.pk,self.user,True)

    def test_reopening_http_permissions_reject_and_conflict(self):
        from .operaciones import solicitar_reapertura, resolver_reapertura
        caja=abrir(self.user,Decimal('0'))
        cerrar(caja.pk,self.user,{'efectivo':0,'transferencia':0,'tarjeta':0},'')
        staff=User.objects.create_user('caja_staff',is_staff=True)
        self.client.force_login(staff)
        self.assertEqual(self.client.post('/caja/',{'accion':'solicitar_reapertura','motivo':'Corregir conteo'}).status_code,302)
        solicitud=caja.reaperturas.get()
        self.assertEqual(self.client.post('/caja/',{'accion':'aprobar_reapertura','solicitud':solicitud.pk}).status_code,403)
        resolver_reapertura(solicitud.pk,self.user,False)
        caja.refresh_from_db()
        self.assertIsNotNone(caja.cerrada_en)
        nueva=solicitar_reapertura(caja.pk,staff,'Nuevo intento autorizado')
        CajaDiaria.objects.create(fecha=timezone.localdate()-timedelta(days=1),inicial=0,abierta_por=self.user)
        with self.assertRaises(ValidationError):
            resolver_reapertura(nueva.pk,self.user,True)
