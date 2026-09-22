from django import forms
from .models import Cliente

class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['nombre', 'apellido', 'nit', 'dpi', 'telefono', 'telefono_alt',
                  'email', 'direccion', 'fecha_nacimiento', 'activo', 'notas']
        widgets = {
            f: forms.TextInput(attrs={'class': 'form-control'})
            for f in ['nombre', 'apellido', 'nit', 'dpi', 'telefono', 'telefono_alt']
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not field.widget.attrs.get('class'):
                if isinstance(field.widget, forms.Textarea):
                    field.widget.attrs.update({'class': 'form-control', 'rows': 3})
                elif isinstance(field.widget, forms.CheckboxInput):
                    field.widget.attrs.update({'class': 'form-check-input'})
                elif isinstance(field.widget, forms.DateInput):
                    field.widget.attrs.update({'class': 'form-control', 'type': 'date'})
                else:
                    field.widget.attrs.update({'class': 'form-control'})
