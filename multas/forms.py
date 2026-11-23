from django import forms
from .models import Pago


class RegistrarPagoForm(forms.Form):
    metodo = forms.ChoiceField(
        label='Método de pago',
        choices=Pago.METODOS,
    )
class CondonarMultaForm(forms.Form):
    justificacion = forms.CharField(
        label='Justificación de la condonación',
        max_length=255,
        strip=True,
        widget=forms.Textarea(attrs={
            'rows': 4,
            'class': 'w-full border border-line rounded-lg p-3 bg-paper',
            'placeholder': 'Explica por qué se autoriza la condonación.',
        }),
    )