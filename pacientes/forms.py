from django import forms
from .models import Paciente, HistorialMedico


class PacienteForm(forms.ModelForm):
    class Meta:
        model = Paciente
        fields = [
            'propietario', 'nombre', 'especie', 'raza', 'sexo', 'fecha_nacimiento',
            'color', 'peso', 'esterilizado', 'microchip', 'alergias',
            'condiciones_cronicas', 'foto', 'estado', 'notas',
        ]

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


class HistorialMedicoForm(forms.ModelForm):
    class Meta:
        model = HistorialMedico
        fields = [
            'motivo', 'anamnesis', 'examen_fisico',
            'peso_consulta', 'temperatura', 'frecuencia_cardiaca', 'frecuencia_respiratoria',
            'diagnostico_presuntivo', 'diagnostico_definitivo',
            'examenes_solicitados', 'resultados_examenes',
            'tratamiento', 'medicamentos', 'cirugia_realizada', 'detalle_cirugia',
            'estado', 'proxima_cita', 'motivo_proxima_cita',
            'veterinario', 'observaciones',
        ]

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


class PostConsultaForm(forms.ModelForm):
    class Meta:
        model = HistorialMedico
        fields = [
            'diagnostico_definitivo',
            'resultados_examenes',
            'descripcion_post_consulta',
            'recomendaciones_propietario',
            'estado',
            'proxima_cita',
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
            'proxima_cita': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'motivo_proxima_cita': forms.TextInput(attrs={'class': 'form-control'}),
        }
