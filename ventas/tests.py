from decimal import Decimal
from uuid import uuid4

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError, PermissionDenied
from django.test import TestCase, override_settings

from clientes.models import Cliente
from productos.models import Producto, MovimientoInventario
from .models import Venta, DetalleVenta, PagoNeonet
from .operaciones import agregar_articulo, cambiar_cantidad


@override_settings(SECURE_SSL_REDIRECT=False, ALLOWED_HOSTS=['testserver'])
class SaleCorrectionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('staff')
        from django.contrib.auth.models import Permission
        self.user.user_permissions.set(Permission.objects.all())
        self.client.force_login(self.user)
        self.owner = Cliente.objects.create(nombre='Ana', apellido='Test')
        self.product = Producto.objects.create(codigo='P', nombre='Producto', precio_compra=5, precio_venta=20, descuento=10, stock=10)
        self.sale = Venta.objects.create(numero='TEST1', cliente=self.owner)

    def test_quantity_reduction_and_removal_return_stock(self):
        item = agregar_articulo(self.sale.pk, self.product.pk, 4, self.user)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 6)
        cambiar_cantidad(self.sale.pk, item.pk, 2, self.user)
        self.product.refresh_from_db()
        self.sale.refresh_from_db()
        self.assertEqual(self.product.stock, 8)
        self.assertEqual(self.sale.total, Decimal('36'))  # one 10% discount, not two
        cambiar_cantidad(self.sale.pk, item.pk, 0, self.user)
        self.product.refresh_from_db()
        self.sale.refresh_from_db()
        self.assertEqual(self.product.stock, 10)
        self.assertEqual(self.sale.total, 0)
        self.assertEqual(MovimientoInventario.objects.filter(tipo='entrada').count(), 2)

    def test_increase_checks_stock_and_preserves_cost(self):
        item = agregar_articulo(self.sale.pk, self.product.pk, 2, self.user)
        with self.assertRaises(ValidationError):
            cambiar_cantidad(self.sale.pk, item.pk, 11, self.user)
        self.product.precio_compra = 9
        self.product.save()
        cambiar_cantidad(self.sale.pk, item.pk, 3, self.user)
        item.refresh_from_db()
        self.assertEqual(item.costo_unitario, 5)

    def test_services_do_not_move_inventory(self):
        self.product.tipo = 'servicio'
        self.product.stock = 0
        self.product.save()
        item = agregar_articulo(self.sale.pk, self.product.pk, 1, self.user)
        cambiar_cantidad(self.sale.pk, item.pk, 2, self.user)
        self.assertFalse(MovimientoInventario.objects.exists())
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 0)

    def test_paid_and_inflight_card_sales_are_immutable(self):
        item = agregar_articulo(self.sale.pk, self.product.pk, 2, self.user)
        self.sale.estado = 'pagada'
        self.sale.save()
        with self.assertRaises(ValidationError):
            cambiar_cantidad(self.sale.pk, item.pk, 1, self.user)
        self.sale.estado = 'pendiente'
        self.sale.save()
        PagoNeonet.objects.create(venta=self.sale, referencia='P1', transaction_uuid=str(uuid4()))
        with self.assertRaises(ValidationError):
            cambiar_cantidad(self.sale.pk, item.pk, 1, self.user)

    def test_invalid_quantities_and_foreign_items(self):
        for quantity in ['-1','0','abc','1.5']:
            self.client.post(f'/ventas/{self.sale.pk}/', {'agregar_item':1,'producto':self.product.pk,'cantidad':quantity})
        self.assertFalse(self.sale.items.exists())
        other = Venta.objects.create(numero='OTHER', cliente=self.owner)
        item = agregar_articulo(other.pk, self.product.pk, 1, self.user)
        self.assertEqual(self.client.post(f'/ventas/{self.sale.pk}/', {'actualizar_item':1,'item':item.pk,'cantidad':3}).status_code, 404)

    def test_comprobante_and_empty_payment(self):
        self.client.post(f'/ventas/{self.sale.pk}/pagar/')
        self.sale.refresh_from_db()
        self.assertEqual(self.sale.estado, 'pendiente')
        response = self.client.get(f'/ventas/{self.sale.pk}/comprobante/')
        self.assertContains(response, 'no acredita un pago')
        self.assertContains(response, 'No sustituye una factura fiscal')

    def test_scan_existing_barcode_adds_sale_line_not_product(self):
        self.product.codigo_barras='7501234567890'
        self.product.save()
        count=Producto.objects.count()
        response=self.client.post(f'/ventas/{self.sale.pk}/', {'agregar_item':'1','codigo_barras':'7501234567890','cantidad':'2'})
        self.assertEqual(response.status_code,302)
        self.assertEqual(self.sale.items.get().producto_id,self.product.pk)
        self.assertEqual(self.sale.items.get().cantidad,2)
        self.assertEqual(Producto.objects.count(),count)
        self.client.post(f'/ventas/{self.sale.pk}/',{'agregar_item':'1','codigo_barras':'NO_EXISTE','cantidad':'1'})
        self.assertEqual(self.sale.items.count(),1)

    def test_discount_threshold_and_approval_guard_cash_and_card(self):
        from .descuentos import aplicar_descuento,resolver_descuento,validar_descuento
        item=agregar_articulo(self.sale.pk,self.product.pk,2,self.user)
        # The catalog's 10% discount also requires approval.
        with self.assertRaises(ValidationError):validar_descuento(self.sale)
        request=aplicar_descuento(self.sale.pk,Decimal('5'),'Atención especial',self.user)
        self.client.post(f'/ventas/{self.sale.pk}/pagar/')
        self.sale.refresh_from_db();self.assertEqual(self.sale.estado,'pendiente')
        self.client.post(f'/ventas/{self.sale.pk}/pagar/neonet/')
        self.assertFalse(self.sale.pagos_neonet.exists())
        with self.assertRaises(PermissionDenied):resolver_descuento(request.pk,self.user,True)
        admin=User.objects.create_user('owner_discount',is_staff=True,is_superuser=True)
        resolver_descuento(request.pk,admin,True)
        self.sale.refresh_from_db();validar_descuento(self.sale)
        cambiar_cantidad(self.sale.pk,item.pk,1,self.user)
        self.sale.refresh_from_db()
        with self.assertRaises(ValidationError):validar_descuento(self.sale)
        below=aplicar_descuento(self.sale.pk,Decimal('4.99'),' ',self.user)
        self.assertIsNone(below)
        self.sale.refresh_from_db();validar_descuento(self.sale)
        self.client.post(f'/ventas/{self.sale.pk}/pagar/')
        self.sale.refresh_from_db();self.assertEqual(self.sale.estado,'pagada')

    def test_stale_or_rejected_request_does_not_authorize_and_link_is_share_only(self):
        from .descuentos import aplicar_descuento,resolver_descuento,validar_descuento
        from django.core.exceptions import PermissionDenied
        item=agregar_articulo(self.sale.pk,self.product.pk,2,self.user)
        request=aplicar_descuento(self.sale.pk,Decimal('8'),'Precio especial',self.user)
        duplicate=aplicar_descuento(self.sale.pk,Decimal('8'),'Precio especial',self.user)
        self.assertEqual(request.pk,duplicate.pk)
        page=self.client.get(f'/ventas/{self.sale.pk}/')
        self.assertContains(page,'Compartir solicitud por WhatsApp')
        self.assertContains(page,'https://wa.me/')
        self.assertEqual(self.client.get('/ventas/descuentos/').status_code,403)
        admin=User.objects.create_user('owner_reject',is_staff=True,is_superuser=True)
        resolver_descuento(request.pk,admin,False)
        self.sale.refresh_from_db()
        with self.assertRaises(ValidationError):validar_descuento(self.sale)
        with self.assertRaises(ValidationError):resolver_descuento(request.pk,admin,True)
        fresh=aplicar_descuento(self.sale.pk,Decimal('8'),'Nueva revisión',self.user)
        cambiar_cantidad(self.sale.pk,item.pk,1,self.user)
        with self.assertRaises(ValidationError):resolver_descuento(fresh.pk,admin,True)
