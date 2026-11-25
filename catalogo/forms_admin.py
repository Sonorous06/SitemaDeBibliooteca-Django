from django import forms

from .models import Ejemplar, Libro


class LibroAdminForm(forms.ModelForm):
    class Meta:
        model = Libro
        fields = "__all__"

    def clean_costo_reposicion(self):
        costo = self.cleaned_data["costo_reposicion"]

        if costo < 0:
            raise forms.ValidationError(
                "El costo de reposición no puede ser negativo."
            )

        return costo

    def clean(self):
        from prestamos.models import Prestamo, Reserva

        datos = super().clean()

        if self.instance.pk and datos.get("activo") is False:
            prestamos_vigentes = Prestamo.objects.filter(
                ejemplar__libro_id=self.instance.pk,
                estado__in=["SOLICITADO", "ACTIVO", "VENCIDO"],
            ).exists()

            reservas_vigentes = Reserva.objects.filter(
                libro_id=self.instance.pk,
                estado__in=["PENDIENTE", "DISPONIBLE"],
            ).exists()

            if prestamos_vigentes or reservas_vigentes:
                self.add_error(
                    "activo",
                    "No puedes inactivar el libro mientras tenga "
                    "préstamos, solicitudes o reservas vigentes.",
                )

        return datos


class EjemplarAdminForm(forms.ModelForm):
    class Meta:
        model = Ejemplar
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.pk:
            for nombre in ("libro", "codigo_inventario"):
                if nombre in self.fields:
                    self.fields[nombre].disabled = True
                    self.fields[nombre].help_text = (
                        "La identidad de un ejemplar existente se conserva."
                    )

    def clean(self):
        from prestamos.models import Prestamo, Reserva

        datos = super().clean()
        estado = datos.get("estado")

        if estado is None:
            return datos

        estados_esperados = set()

        if self.instance.pk:
            estados_prestamos = Prestamo.objects.filter(
                ejemplar_id=self.instance.pk,
                estado__in=["SOLICITADO", "ACTIVO", "VENCIDO"],
            ).values_list("estado", flat=True)

            for estado_prestamo in estados_prestamos:
                estados_esperados.add(
                    "RESERVADO"
                    if estado_prestamo == "SOLICITADO"
                    else "PRESTADO"
                )

            if Reserva.objects.filter(
                ejemplar_asignado_id=self.instance.pk,
                estado="DISPONIBLE",
            ).exists():
                estados_esperados.add("RESERVADO")

        if estados_esperados:
            if len(estados_esperados) > 1:
                self.add_error(
                    "estado",
                    "Hay asignaciones incompatibles en este ejemplar. "
                    "Revisa sus préstamos y reservas.",
                )
            elif estado not in estados_esperados:
                self.add_error(
                    "estado",
                    "El ejemplar tiene un préstamo o reserva vigente. "
                    "Utiliza las pantallas de entrega, devolución, "
                    "cancelación o incidencia para cambiar su estado.",
                )

        elif estado in ("PRESTADO", "RESERVADO"):
            self.add_error(
                "estado",
                "Este estado se asigna desde los flujos de "
                "préstamo y reserva, no manualmente.",
            )

        return datos