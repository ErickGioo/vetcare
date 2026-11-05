from decimal import Decimal
from uuid import uuid4
from django.test import TestCase,override_settings
from django.contrib.auth.models import User,Permission
from django.core.exceptions import ValidationError,PermissionDenied
from clientes.models import Cliente
from productos.models import Producto
from ventas.models import Venta
from ventas.operaciones import agregar_articulo,cambiar_cantidad
from caja.operaciones import abrir,cerrar,registrar_cobro
from caja.models import CajaDiaria
from .models import Ubicacion,Existencia,Traslado
from .operaciones import trasladar,asegurar_existencias


@override_settings(SECURE_SSL_REDIRECT=False,ALLOWED_HOSTS=['testserver'])
class UbicacionesTests(TestCase):
    def setUp(self):
        self.admin=User.objects.create_user('owner',is_staff=True,is_superuser=True)
        self.seller=User.objects.create_user('vendedor')
        self.seller.user_permissions.add(*Permission.objects.filter(content_type__app_label='ventas'))
        self.central=Ubicacion.objects.get(central=True)
        self.branch=Ubicacion.objects.create(nombre='Punto A')
        self.branch.usuarios.add(self.seller)
        self.product=Producto.objects.create(codigo='LOCAL',nombre='Producto',stock=10,precio_venta=20,precio_mayorista=15)
        asegurar_existencias(self.product)
        self.owner=Cliente.objects.create(nombre='Comprador')

    def move(self,qty=4,token=None):
        return trasladar(self.product.pk,self.central.pk,self.branch.pk,qty,self.admin,'Asignación',token or uuid4())

    def test_transfer_conserves_stock_and_deduplicates(self):
        token=uuid4()
        first=self.move(token=token);second=self.move(token=token)
        self.assertEqual(first.pk,second.pk)
        self.assertEqual(Traslado.objects.count(),1)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock,10)
        self.assertEqual(Existencia.objects.get(producto=self.product,ubicacion=self.central).cantidad,6)
        self.assertEqual(Existencia.objects.get(producto=self.product,ubicacion=self.branch).cantidad,4)
        with self.assertRaises(ValidationError):self.move(qty=7)
        self.assertEqual(Traslado.objects.count(),1)

    def test_sale_uses_only_local_stock_and_returns_to_same_location(self):
        self.move()
        sale=Venta.objects.create(numero='BRANCH',cliente=self.owner,punto_venta=self.branch)
        item=agregar_articulo(sale.pk,self.product.pk,3,self.seller)
        with self.assertRaises(ValidationError):agregar_articulo(sale.pk,self.product.pk,2,self.seller)
        self.assertEqual(sale.items.count(),1)
        cambiar_cantidad(sale.pk,item.pk,1,self.seller)
        self.assertEqual(Existencia.objects.get(producto=self.product,ubicacion=self.branch).cantidad,3)
        self.assertEqual(Existencia.objects.get(producto=self.product,ubicacion=self.central).cantidad,6)
        self.product.refresh_from_db();self.assertEqual(self.product.stock,9)
        foreign=Venta.objects.create(numero='OTHERPOINT',cliente=self.owner,punto_venta=self.central)
        with self.assertRaises(PermissionDenied):agregar_articulo(foreign.pk,self.product.pk,1,self.seller)
        self.client.force_login(self.seller)
        self.assertEqual(self.client.get(f'/ventas/{foreign.pk}/').status_code,403)
        self.assertNotContains(self.client.get('/ventas/'),'OTHERPOINT')
        self.assertEqual(self.client.get('/inventario/').status_code,403)

    def test_wholesale_uses_separate_price(self):
        sale=Venta.objects.create(numero='WHOLE',cliente=self.owner,mayorista=True)
        item=agregar_articulo(sale.pk,self.product.pk,2,self.admin)
        self.assertEqual(item.precio_unitario,Decimal('15'))
        sale.refresh_from_db();self.assertEqual(sale.total,30)
        self.product.precio_mayorista=None;self.product.save()
        with self.assertRaises(ValidationError):agregar_articulo(sale.pk,self.product.pk,1,self.admin)
        self.assertEqual(sale.items.count(),1)

    def test_separate_daily_boxes_and_unassigned_receipts(self):
        central_box=abrir(self.admin,Decimal('20'),self.central.pk)
        branch_box=abrir(self.admin,Decimal('50'),self.branch.pk)
        self.assertEqual(CajaDiaria.objects.count(),2)
        sale=Venta.objects.create(numero='BOXBR',cliente=self.owner,punto_venta=self.branch,total=100,estado='pagada')
        registrar_cobro(sale)
        self.assertEqual(branch_box.cobros.count(),1)
        self.assertEqual(central_box.cobros.count(),0)
        cerrar(branch_box.pk,self.admin,{'efectivo':150,'tarjeta':0,'transferencia':0},'')
        branch_box.refresh_from_db();self.assertEqual(Decimal(branch_box.esperado['efectivo']),150)

    def test_editing_stale_product_does_not_restore_sold_stock(self):
        self.move()
        stale=Producto.objects.get(pk=self.product.pk)
        sale=Venta.objects.create(numero='STALE',cliente=self.owner,punto_venta=self.branch)
        agregar_articulo(sale.pk,self.product.pk,2,self.seller)
        stale.precio_compra=Decimal('7')
        stale.save()
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock,8)
        self.assertEqual(Existencia.objects.get(producto=self.product,ubicacion=self.branch).cantidad,2)

    def test_management_pages_and_new_wholesale_sale_form(self):
        self.client.force_login(self.admin)
        for page in ['/inventario/','/inventario/puntos/','/ventas/descuentos/','/ventas/?canal=mayorista','/ventas/nueva/?mayorista=1']:
            self.assertEqual(self.client.get(page).status_code,200,page)
        self.assertEqual(self.client.get('/ventas/nueva/?mayorista=1').context['form'].initial['mayorista'],True)
