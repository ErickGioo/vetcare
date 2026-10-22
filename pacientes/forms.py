from decimal import Decimal

from django import forms
from .models import Especie, HistorialMedico, Paciente, Raza
from productos.models import Producto
from django.utils import timezone


DATE_WIDGET = forms.DateInput(
    format='%d/%m/%Y',
    attrs={
        'class': 'form-control',
        'placeholder': 'dd/mm/aaaa',
        'inputmode': 'numeric',
        'autocomplete': 'off',
    },
)


class PacienteForm(forms.ModelForm):
    class Meta:
        model = Paciente
        fields = [
            'propietario', 'nombre', 'especie', 'raza', 'sexo', 'fecha_nacimiento',
            'color', 'peso', 'esterilizado', 'microchip', 'alergias',
            'condiciones_cronicas', 'foto', 'estado', 'notas',
        ]
        widgets = {'fecha_nacimiento': DATE_WIDGET}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            w = field.widget
            if isinstance(w, forms.CheckboxInput):
                w.attrs['class'] = 'form-check-input'
            elif isinstance(w, forms.Select):
                w.attrs['class'] = 'form-select'
            elif isinstance(w, forms.Textarea):
                w.attrs.update({'class': 'form-control', 'rows': 3})
            else:
                w.attrs['class'] = 'form-control'
        self.fields['fecha_nacimiento'].input_formats = ['%d/%m/%Y', '%Y-%m-%d']
        self.fields['fecha_nacimiento'].help_text = 'Formato: dd/mm/aaaa'
        species = self.data.get(self.add_prefix('especie')) if self.is_bound else self.instance.especie_id
        try:
            species = int(species)
        except (ValueError, TypeError):
            species = None
        self.fields['raza'].queryset = Raza.objects.filter(especie_id=species).order_by('nombre') if species else Raza.objects.none()


class RevisionValidation:
    def clean(self):
        data = super().clean()
        day, hour = data.get('proxima_cita'), data.get('proxima_hora')
        if day and not hour:
            self.add_error('proxima_hora', 'Indica la hora para agregar la revisión a la agenda.')
        if hour and not day:
            self.add_error('proxima_cita', 'Indica la fecha de revisión.')
        if day and hour:
            from datetime import datetime
            when = timezone.make_aware(datetime.combine(day, hour))
            if when < timezone.now() and (day != self.instance.proxima_cita or hour != self.instance.proxima_hora):
                self.add_error('proxima_cita', 'La revisión debe agendarse en una fecha y hora futuras.')
        return data


class ServicioConsultaForm(forms.Form):
    servicio = forms.ModelChoiceField(queryset=Producto.objects.none(), label='Servicio a facturar',
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text='La atención genera una venta pendiente. El ingreso se registra al confirmar el pago.')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['servicio'].queryset = Producto.objects.filter(activo=True, tipo='servicio', precio_venta__gt=0, descuento__gte=0, descuento__lt=100).order_by('nombre')
        self.fields['servicio'].empty_label = 'Selecciona el servicio de esta atención'
        self.fields['servicio'].label_from_instance = lambda p: f'{p.nombre} · Q{p.precio_final:.2f}'


class ServicioRapidoForm(forms.Form):
    nombre = forms.CharField(max_length=200, strip=True)
    precio = forms.DecimalField(min_value=Decimal('0.01'), max_value=Decimal('99999999.99'), max_digits=10, decimal_places=2)
    costo = forms.DecimalField(required=False, min_value=Decimal('0'), max_value=Decimal('99999999.99'), max_digits=10, decimal_places=2)


class HistorialMedicoForm(RevisionValidation, forms.ModelForm):
    class Meta:
        model = HistorialMedico
        fields = [
            'motivo', 'anamnesis', 'examen_fisico',
            'peso_consulta', 'temperatura', 'frecuencia_cardiaca', 'frecuencia_respiratoria',
            'diagnostico_presuntivo', 'diagnostico_definitivo',
            'examenes_solicitados', 'resultados_examenes',
            'tratamiento', 'medicamentos', 'cirugia_realizada', 'detalle_cirugia',
            'estado', 'proxima_cita', 'proxima_hora', 'motivo_proxima_cita',
            'veterinario', 'observaciones',
        ]
        widgets = {'proxima_cita': DATE_WIDGET, 'proxima_hora': forms.TimeInput(format='%H:%M', attrs={'type':'time'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            w = field.widget
            if isinstance(w, forms.CheckboxInput):
                w.attrs['class'] = 'form-check-input'
            elif isinstance(w, forms.Select):
                w.attrs['class'] = 'form-select'
            elif isinstance(w, forms.Textarea):
                rows = 4 if name in ('diagnostico_definitivo', 'tratamiento', 'anamnesis') else 3
                w.attrs.update({'class': 'form-control', 'rows': rows})
            else:
                w.attrs['class'] = 'form-control'
        self.fields['proxima_cita'].input_formats = ['%d/%m/%Y', '%Y-%m-%d']
        self.fields['proxima_cita'].help_text = 'Formato: dd/mm/aaaa'


class PostConsultaForm(RevisionValidation, forms.ModelForm):
    class Meta:
        model = HistorialMedico
        fields = [
            'diagnostico_definitivo',
            'resultados_examenes',
            'descripcion_post_consulta',
            'recomendaciones_propietario',
            'estado',
            'proxima_cita',
            'proxima_hora',
            'motivo_proxima_cita',
            'observaciones',
        ]
        widgets = {
            'diagnostico_definitivo': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'descripcion_post_consulta': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'recomendaciones_propietario': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'resultados_examenes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'proxima_cita': DATE_WIDGET,
            'proxima_hora': forms.TimeInput(format='%H:%M', attrs={'type':'time', 'class':'form-control'}),
            'motivo_proxima_cita': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['proxima_cita'].input_formats = ['%d/%m/%Y', '%Y-%m-%d']
        self.fields['proxima_cita'].help_text = 'Formato: dd/mm/aaaa'


class EspecieForm(forms.ModelForm):
    class Meta:
        model = Especie
        fields = ['nombre']
        widgets = {'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Canino'})}

    def clean_nombre(self):
        nombre = self.cleaned_data['nombre'].strip()
        if Especie.objects.filter(nombre__iexact=nombre).exists():
            raise forms.ValidationError('Esta especie ya existe.')
        return nombre


class RazaForm(forms.ModelForm):
    class Meta:
        model = Raza
        fields = ['especie', 'nombre']
        widgets = {
            'especie': forms.Select(attrs={'class': 'form-select'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Labrador Retriever'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        especie = cleaned_data.get('especie')
        nombre = (cleaned_data.get('nombre') or '').strip()
        if especie and nombre and Raza.objects.filter(especie=especie, nombre__iexact=nombre).exists():
            self.add_error('nombre', 'Esta raza ya existe para la especie seleccionada.')
        return cleaned_data
