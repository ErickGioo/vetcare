from django import forms
from .models import Producto, Categoria, MovimientoInventario

class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nombre', 'descripcion', 'activa', 'es_servicio']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'activa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_es_servicio(self):
        value = self.cleaned_data['es_servicio']
        if self.instance.pk and value != self.instance.es_servicio and Producto.objects.filter(categoria=self.instance).exists():
            raise forms.ValidationError('Esta categoría tiene productos. Crea otra categoría para cambiar el manejo de inventario.')
        return value

class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = [
            'codigo', 'nombre', 'categoria', 'proveedor',
            'descripcion', 'precio_compra', 'precio_venta', 'descuento',
            'stock', 'stock_minimo', 'unidad_medida', 'requiere_receta',
            'activo', 'imagen'
        ]
        widgets = {
            'codigo': forms.TextInput(attrs={'class': 'form-control'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'proveedor': forms.Select(attrs={'class': 'form-select'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'precio_compra': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'precio_venta': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'descuento': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control'}),
            'stock_minimo': forms.NumberInput(attrs={'class': 'form-control'}),
            'unidad_medida': forms.TextInput(attrs={'class': 'form-control'}),
            'requiere_receta': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['codigo'].required = False
        self.fields['codigo'].help_text = 'Opcional: ingresa un código de barras o deja vacío para generar un código único.'
        self.fields['categoria'].required = True
        self.fields['categoria'].queryset = Categoria.objects.filter(activa=True)

    def clean_codigo(self):
        from uuid import uuid4
        return self.cleaned_data.get('codigo') or self.instance.codigo or ('PROD-' + uuid4().hex[:16].upper())

    def clean(self):
        data = super().clean()
        category = data.get('categoria')
        if category and self.instance.pk and (self.instance.tipo == 'servicio') != category.es_servicio:
            self.add_error('categoria', 'No se puede convertir un servicio en artículo físico o viceversa. Crea otro registro para conservar el historial.')
        if category and category.es_servicio:
            data['stock'] = 0
            data['stock_minimo'] = 0
        return data

    def save(self, commit=True):
        product = super().save(commit=False)
        product.tipo = 'servicio' if product.categoria.es_servicio else (product.tipo if product.tipo != 'servicio' else 'otro')
        if commit:
            product.save()
            self.save_m2m()
        return product

class AjusteInventarioForm(forms.Form):
    TIPO_CHOICES = [('entrada', 'Entrada'), ('salida', 'Salida'), ('ajuste', 'Ajuste')]
    tipo = forms.ChoiceField(choices=TIPO_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))
    cantidad = forms.IntegerField(min_value=1, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    motivo = forms.CharField(max_length=200, widget=forms.TextInput(attrs={'class': 'form-control'}))
    referencia = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
