from decimal import Decimal
from django import forms


def importe(label):
    return forms.DecimalField(label=label, min_value=Decimal('0'), max_value=Decimal('99999999999.99'), max_digits=14, decimal_places=2,
        widget=forms.NumberInput(attrs={'class':'form-control', 'step':'0.01', 'min':'0'}))


class AperturaForm(forms.Form):
    inicial = importe('Efectivo inicial (Q)')


class CierreForm(forms.Form):
    efectivo = importe('Efectivo contado en caja (Q), incluye fondo inicial')
    transferencia = importe('Transferencias verificadas en banco (Q)')
    tarjeta = importe('Total verificado en terminal / NeoNet (Q)')
    observaciones = forms.CharField(required=False, max_length=2000, widget=forms.Textarea(attrs={'class':'form-control', 'rows':3}))


class ReaperturaForm(forms.Form):
    motivo = forms.CharField(label='Motivo de reapertura', min_length=5, max_length=2000,
        widget=forms.Textarea(attrs={'class':'form-control','rows':2}))
