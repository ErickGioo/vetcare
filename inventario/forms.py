from django import forms
from django.contrib.auth.models import User
from productos.models import Producto
from .models import Ubicacion


class PuntoForm(forms.ModelForm):
    class Meta:
        model=Ubicacion
        fields=['nombre','usuarios']
        widgets={'nombre':forms.TextInput(attrs={'class':'form-control'}),'usuarios':forms.SelectMultiple(attrs={'class':'form-select'})}

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields['usuarios'].queryset=User.objects.filter(is_active=True,is_superuser=False)
        self.fields['usuarios'].help_text='La asignación limita ubicaciones; no otorga permisos para vender o cobrar.'


class TrasladoForm(forms.Form):
    origen=forms.ModelChoiceField(queryset=Ubicacion.objects.filter(activa=True))
    destino=forms.ModelChoiceField(queryset=Ubicacion.objects.filter(activa=True))
    producto=forms.ModelChoiceField(queryset=Producto.objects.filter(activo=True).exclude(tipo='servicio'))
    cantidad=forms.IntegerField(min_value=1,max_value=2147483647)
    motivo=forms.CharField(max_length=300)
    token=forms.UUIDField(widget=forms.HiddenInput)

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        for field in self.fields.values():
            field.widget.attrs['class']='form-select' if isinstance(field.widget,forms.Select) else 'form-control'
