from django.db import migrations


def clasificar(apps, schema_editor):
    Producto = apps.get_model('productos', 'Producto')
    Categoria = apps.get_model('productos', 'Categoria')
    alias = schema_editor.connection.alias
    labels = dict(Producto._meta.get_field('tipo').choices)
    for product in Producto.objects.using(alias).select_related('categoria').all():
        service = product.tipo == 'servicio'
        category = product.categoria
        if category is None:
            category, _ = Categoria.objects.using(alias).get_or_create(nombre=labels.get(product.tipo,'Otros'), es_servicio=service, defaults={'activa':True})
        elif service:
            if Producto.objects.using(alias).filter(categoria=category).exclude(tipo='servicio').exists():
                category, _ = Categoria.objects.using(alias).get_or_create(nombre=(category.nombre[:85]+' · Servicios'), es_servicio=True, defaults={'activa':category.activa})
            else:
                Categoria.objects.using(alias).filter(pk=category.pk).update(es_servicio=True)
        Producto.objects.using(alias).filter(pk=product.pk).update(categoria=category)


class Migration(migrations.Migration):
    dependencies = [('productos','0002_categoria_es_servicio')]
    operations = [migrations.RunPython(clasificar, migrations.RunPython.noop)]
