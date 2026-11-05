from django.db import migrations


def inicializar(apps,schema_editor):
    alias=schema_editor.connection.alias
    Ubicacion=apps.get_model('inventario','Ubicacion')
    Existencia=apps.get_model('inventario','Existencia')
    Producto=apps.get_model('productos','Producto')
    central=Ubicacion.objects.using(alias).create(nombre='Almacén central',central=True)
    if central.pk!=1:
        raise RuntimeError('La ubicación inicial debe ser 1.')
    for product in Producto.objects.using(alias).exclude(tipo='servicio').iterator():
        if product.stock<0:
            raise RuntimeError('Hay productos con stock negativo. Conciliar antes de migrar.')
        Existencia.objects.using(alias).create(ubicacion=central,producto=product,cantidad=product.stock)


class Migration(migrations.Migration):
    dependencies=[('inventario','0001_initial')]
    operations=[migrations.RunPython(inicializar,migrations.RunPython.noop)]
