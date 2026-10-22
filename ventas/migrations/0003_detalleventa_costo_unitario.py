from decimal import Decimal

from django.db import migrations, models


def copiar_costo_actual(apps, schema_editor):
    """Inicializa ventas existentes con el costo disponible del producto.

    Las ventas nuevas guardan su costo al momento de vender; este valor es la
    mejor referencia recuperable para los registros anteriores a la mejora.
    """
    DetalleVenta = apps.get_model('ventas', 'DetalleVenta')
    for detalle in DetalleVenta.objects.select_related('producto').all().iterator():
        detalle.costo_unitario = detalle.producto.precio_compra or Decimal('0.00')
        detalle.save(update_fields=['costo_unitario'])


class Migration(migrations.Migration):
    dependencies = [('ventas', '0002_pagoneonet')]

    operations = [
        migrations.AddField(
            model_name='detalleventa',
            name='costo_unitario',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.RunPython(copiar_costo_actual, migrations.RunPython.noop),
    ]
