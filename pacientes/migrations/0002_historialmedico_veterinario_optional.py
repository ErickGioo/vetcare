# Permite asignar automáticamente el usuario autenticado al registrar una consulta.
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('pacientes', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='historialmedico',
            name='veterinario',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='consultas',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Médico tratante',
            ),
        ),
    ]
