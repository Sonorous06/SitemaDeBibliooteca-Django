from decimal import Decimal

from django import forms

from .models import PoliticaPrestamo


class PoliticaPrestamoForm(forms.ModelForm):
    class Meta:
        model = PoliticaPrestamo

        fields = [
            "dias_prestamos",
            "max_libros",
            "max_renovaciones",
            "multa_por_dia",
            "multa_maxima",
            "horas_para_recoger",
        ]

        labels = {
            "dias_prestamos": "Días de préstamo",
            "max_libros": "Máximo de libros simultáneos",
            "max_renovaciones": "Renovaciones permitidas",
            "multa_por_dia": "Multa por día de retraso ($)",
            "multa_maxima": "Tope de multa por retraso ($)",
            "horas_para_recoger": "Horas para recoger solicitudes y reservas",
        }

        help_texts = {
            "dias_prestamos": "Días naturales desde la entrega o renovación.",
            "max_libros": "Incluye solicitudes pendientes de recoger.",
            "max_renovaciones": "Escribe 0 para desactivar las renovaciones.",
            "multa_por_dia": "Importe utilizado al calcular nuevas multas.",
            "multa_maxima": "Este tope corresponde únicamente al retraso.",
            "horas_para_recoger": "Plazo para nuevas solicitudes y asignaciones.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        positivos = {
            "dias_prestamos",
            "max_libros",
            "horas_para_recoger",
        }

        enteros = positivos | {"max_renovaciones"}

        for nombre, campo in self.fields.items():
            campo.widget.attrs["class"] = (
                "w-full px-4 py-3 rounded-lg border "
                "border-line bg-cream text-coffee"
            )

            if nombre in enteros:
                campo.min_value = 1 if nombre in positivos else 0
                campo.max_value = 32767
                campo.widget.attrs["min"] = campo.min_value
                campo.widget.attrs["max"] = campo.max_value
                campo.widget.attrs["step"] = 1
            else:
                campo.min_value = Decimal("0.00")
                campo.widget.attrs["min"] = "0"
                campo.widget.attrs["step"] = "0.01"

    def clean(self):
        datos = super().clean()

        # Validación en el servidor, además de los controles del navegador.
        for nombre in (
            "dias_prestamos",
            "max_libros",
            "horas_para_recoger",
        ):
            valor = datos.get(nombre)
            if valor is not None and not 1 <= valor <= 32767:
                self.add_error(
                    nombre,
                    "Escribe un número entero entre 1 y 32767.",
                )

        renovaciones = datos.get("max_renovaciones")
        if renovaciones is not None and not 0 <= renovaciones <= 32767:
            self.add_error(
                "max_renovaciones",
                "Escribe un número entero entre 0 y 32767.",
            )

        for nombre in ("multa_por_dia", "multa_maxima"):
            valor = datos.get(nombre)
            if valor is not None and valor < 0:
                self.add_error(
                    nombre,
                    "El importe no puede ser negativo.",
                )

        return datos