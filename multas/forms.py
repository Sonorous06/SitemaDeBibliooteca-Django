from django import forms
from .models import Pago


class RegistrarPagoForm(forms.Form):
    metodo = forms.ChoiceField(
        label='Método de pago',
        choices=Pago.METODOS,
    )