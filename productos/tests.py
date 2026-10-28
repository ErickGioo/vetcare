from django.test import TestCase, override_settings
from django.contrib.auth.models import User, Permission
from .models import Producto, Categoria
from .forms import ProductoForm, CategoriaForm


@override_settings(SECURE_SSL_REDIRECT=False, ALLOWED_HOSTS=['testserver'])
class CatalogoPermisosTests(TestCase):
    def setUp(self):
        self.user=User.objects.create_user('Recepcionista',is_staff=True)
        self.client.force_login(self.user)
        self.category=Categoria.objects.create(nombre='Alimentos')

    def data(self, **extra):
        return dict(nombre='Producto',categoria=self.category.pk,precio_compra='5',precio_venta='20',descuento='0',stock='10',stock_minimo='2',unidad_medida='unidad',activo='on',**extra)

    def test_category_only_auto_code_manual_code_and_unique(self):
        form=ProductoForm(self.data())
        self.assertNotIn('tipo',form.fields)
        self.assertTrue(form.is_valid(),form.errors)
        product=form.save()
        self.assertTrue(product.codigo.startswith('PROD-'))
        other=ProductoForm(self.data(codigo='7501234'))
        self.assertTrue(other.is_valid(),other.errors)
        other.save()
        duplicate=ProductoForm(self.data(codigo='7501234'))
        self.assertFalse(duplicate.is_valid())
        self.assertIn('codigo',duplicate.errors)
        edited=ProductoForm(self.data(),instance=product)
        self.assertTrue(edited.is_valid(),edited.errors)
        self.assertEqual(edited.save().codigo,product.codigo)

    def test_service_category_keeps_inventory_semantics(self):
        category=Categoria.objects.create(nombre='Servicios',es_servicio=True)
        data=self.data();data['categoria']=category.pk
        form=ProductoForm(data)
        self.assertTrue(form.is_valid(),form.errors)
        product=form.save()
        self.assertEqual(product.tipo,'servicio')
        self.assertEqual(product.stock,0)
        category_form=CategoriaForm({'nombre':'Servicios','activa':'on'},instance=category)
        self.assertFalse(category_form.is_valid())
        edit=ProductoForm(self.data(),instance=product)
        self.assertFalse(edit.is_valid())

    def test_restricted_staff_cannot_bypass_by_url_or_post(self):
        for path in ['/productos/','/productos/nuevo/','/ventas/','/pacientes/','/clientes/','/empleados/','/proveedores/','/citas/','/informes/','/caja/']:
            self.assertEqual(self.client.get(path).status_code,403,path)
        self.assertEqual(self.client.post('/productos/nuevo/',self.data()).status_code,403)
        self.assertFalse(Producto.objects.exists())
        self.user.user_permissions.add(Permission.objects.get(codename='view_producto'))
        self.assertEqual(self.client.get('/productos/').status_code,200)
        self.assertEqual(self.client.post('/productos/nuevo/',self.data()).status_code,403)
        self.assertNotContains(self.client.get('/'), 'href="/ventas/"')
        self.user.user_permissions.add(Permission.objects.get(codename='add_producto'))
        self.assertEqual(self.client.post('/productos/nuevo/',self.data()).status_code,302)
        product=Producto.objects.get()
        self.assertEqual(self.client.post(f'/productos/{product.pk}/editar/',self.data()).status_code,403)

    def test_group_permissions_apply_without_staff_bypass(self):
        from django.contrib.auth.models import Group
        group=Group.objects.create(name='Recepción')
        group.permissions.add(Permission.objects.get(codename='view_cita'))
        self.user.groups.add(group)
        self.assertEqual(self.client.get('/citas/').status_code,200)
        self.assertEqual(self.client.get('/citas/nueva/').status_code,403)
        self.assertEqual(self.client.get('/citas/1/estado/completada/').status_code,403)
