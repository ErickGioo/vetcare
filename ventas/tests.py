from decimal import Decimal
from uuid import uuid4

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
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
