from django.db import migrations


def crear_control(apps, schema_editor):
    apps.get_model('caja', 'ControlCaja').objects.using(schema_editor.connection.alias).get_or_create(pk=1)


class Migration(migrations.Migration):
    dependencies = [('caja', '0001_initial')]
    operations = [migrations.RunPython(crear_control, migrations.RunPython.noop)]
