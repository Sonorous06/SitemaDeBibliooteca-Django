from django import forms


class PrestamoMostradorForm(forms.Form):
    usuario = forms.CharField(
        label="Usuario del lector",
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": (
                    "w-full px-4 py-3 rounded-lg border "
                    "border-line bg-cream text-coffee"
                ),
                "placeholder": "Ejemplo: francisco",
                "autocomplete": "off",
            }
        ),
    )

    codigo_inventario = forms.CharField(
        label="Código del ejemplar",
        max_length=30,
        widget=forms.TextInput(
            attrs={
                "class": (
                    "w-full px-4 py-3 rounded-lg border "
                    "border-line bg-cream text-coffee"
                ),
                "placeholder": "Ejemplo: INV-PRG-02",
                "autocomplete": "off",
            }
        ),
    )