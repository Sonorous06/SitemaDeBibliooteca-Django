from django import forms

from .forms_admin import EjemplarAdminForm, LibroAdminForm
from .models import Autor, Categoria, Editorial, Ejemplar, Libro, LibroAutor


def dar_estilo(formulario):
    for campo in formulario.fields.values():
        if isinstance(campo.widget, forms.CheckboxInput):
            campo.widget.attrs["class"] = "h-4 w-4 accent-navy"
        else:
            campo.widget.attrs["class"] = (
                "w-full px-3 py-2.5 bg-cream border border-line "
                "rounded-lg text-coffee focus:outline-none focus:ring-2 "
                "focus:ring-steel/30"
            )


class LibroAcervoForm(LibroAdminForm):
    autores = forms.ModelMultipleChoiceField(
        queryset=Autor.objects.order_by("apellidos", "nombre", "pk"),
        help_text="Puedes seleccionar varios autores manteniendo Ctrl o Command.",
        widget=forms.SelectMultiple(attrs={"size": 6}),
    )

    class Meta:
        model = Libro
        fields = (
            "isbn",
            "titulo",
            "subtitulo",
            "categoria",
            "editorial",
            "autores",
            "anio_publicacion",
            "edicion",
            "idioma",
            "num_paginas",
            "descripcion",
            "portada",
            "costo_reposicion",
            "activo",
        )
        widgets = {"descripcion": forms.Textarea(attrs={"rows": 4})}
        labels = {
            "isbn": "ISBN o identificador de demostración",
            "anio_publicacion": "Año de publicación",
            "num_paginas": "Número de páginas",
            "costo_reposicion": "Costo de reposición (MXN)",
            "activo": "Libro activo",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.initial["autores"] = list(
                LibroAutor.objects.filter(libro=self.instance)
                .order_by("orden", "pk")
                .values_list("autor_id", flat=True)
            )
        dar_estilo(self)

    def clean_anio_publicacion(self):
        valor = self.cleaned_data.get("anio_publicacion")
        if valor is not None and valor < 1:
            raise forms.ValidationError("El año debe ser mayor que cero.")
        return valor

    def clean_num_paginas(self):
        valor = self.cleaned_data.get("num_paginas")
        if valor is not None and valor < 1:
            raise forms.ValidationError(
                "El número de páginas debe ser positivo."
            )
        return valor


class EjemplarAcervoForm(EjemplarAdminForm):
    class Meta:
        model = Ejemplar
        fields = (
            "codigo_inventario",
            "ubicacion",
            "estado",
            "fecha_adquisicion",
            "observaciones",
        )
        widgets = {
            "fecha_adquisicion": forms.DateInput(
                format="%Y-%m-%d", attrs={"type": "date"}
            ),
            "observaciones": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        dar_estilo(self)


class AutorAcervoForm(forms.ModelForm):
    class Meta:
        model = Autor
        fields = ("nombre", "apellidos", "nacionalidad")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["apellidos"].required = False
        dar_estilo(self)


class CategoriaAcervoForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ("nombre", "descripcion")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        dar_estilo(self)


class EditorialAcervoForm(forms.ModelForm):
    class Meta:
        model = Editorial
        fields = ("nombre", "pais")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        dar_estilo(self)
