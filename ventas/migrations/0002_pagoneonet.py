# Generated manually for NeoNet/CyberSource payment tracking.
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('ventas', '0001_initial')]

    operations = [
        migrations.CreateModel(
            name='PagoNeonet',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('referencia', models.CharField(max_length=50, unique=True)),
                ('transaction_uuid', models.CharField(max_length=36, unique=True)),
                ('estado', models.CharField(choices=[('pendiente', 'Pendiente'), ('aceptado', 'Aceptado'), ('rechazado', 'Rechazado'), ('error', 'Error')], default='pendiente', max_length=12)),
                ('transaction_id', models.CharField(blank=True, max_length=80)),
                ('razon', models.CharField(blank=True, max_length=20)),
                ('mensaje', models.CharField(blank=True, max_length=255)),
                ('respuesta', models.JSONField(blank=True, default=dict)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
                ('venta', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='pagos_neonet', to='ventas.venta')),
            ],
            options={'verbose_name': 'Pago NeoNet', 'verbose_name_plural': 'Pagos NeoNet'},
        ),
    ]
