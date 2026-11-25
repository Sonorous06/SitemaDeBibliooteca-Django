from django.contrib import admin
from django.db import transaction

from .forms_admin import EjemplarAdminForm, LibroAdminForm
from .models import (
    Autor,
    Categoria,
    Editorial,
    Ejemplar,
    Libro,
    LibroAutor,
    SugerenciaAdquisicion,
)


def atender_disponibilidad(ejemplar):
    """Debe ejecutarse dentro de una transacción."""
    if ejemplar.estado == "DISPONIBLE" and ejemplar.libro.activo:
        from django.utils import timezone
        from prestamos.views import asignar_reserva_o_liberar

        asignar_reserva_o_liberar(
            ejemplar,
            timezone.now(),
        )


class LibroAutorInline(admin.TabularInline):
    model = LibroAutor
    fields = ("autor", "orden")
    extra = 1


class EjemplarInline(admin.TabularInline):
    model = Ejemplar
    form = EjemplarAdminForm
    extra = 1
    can_delete = False


@admin.register(Libro)
class LibroAdmin(admin.ModelAdmin):
    form = LibroAdminForm

    list_display = (
        "titulo",
        "isbn",
        "categoria",
        "editorial",
        "activo",
    )

    search_fields = ("titulo", "isbn")
    list_filter = ("categoria", "editorial", "activo")
    inlines = [LibroAutorInline, EjemplarInline]

    def has_delete_permission(self, request, obj=None):
        # Conservar libros y sus relaciones. Usar activo=False.
        return False

    def changeform_view(
        self,
        request,
        object_id=None,
        form_url="",
        extra_context=None,
    ):
        if request.method == "POST":
            with transaction.atomic():
                if object_id is not None:
                    libro = (
                        Libro.objects.select_for_update()
                        .filter(pk=object_id)
                        .first()
                    )

                    if libro:
                        list(
                            Ejemplar.objects.select_for_update()
                            .filter(libro=libro)
                            .order_by("pk")
                        )

                return super().changeform_view(
                    request,
                    object_id,
                    form_url,
                    extra_context,
                )

        return super().changeform_view(
            request,
            object_id,
            form_url,
            extra_context,
        )

    def save_formset(self, request, form, formset, change):
        if formset.model is not Ejemplar:
            return super().save_formset(
                request,
                form,
                formset,
                change,
            )

        ejemplares = formset.save(commit=False)

        for ejemplar in ejemplares:
            ejemplar.save()
            atender_disponibilidad(ejemplar)

        formset.save_m2m()


@admin.register(Ejemplar)
class EjemplarAdmin(admin.ModelAdmin):
    form = EjemplarAdminForm

    list_display = (
        "codigo_inventario",
        "libro",
        "estado",
        "ubicacion",
    )

    search_fields = (
        "codigo_inventario",
        "libro__titulo",
        "libro__isbn",
    )

    list_filter = ("estado",)

    def has_delete_permission(self, request, obj=None):
        # Conservar ejemplares. Usar estado BAJA cuando corresponda.
        return False

    def changeform_view(
        self,
        request,
        object_id=None,
        form_url="",
        extra_context=None,
    ):
        if request.method == "POST":
            with transaction.atomic():
                if object_id is not None:
                    referencia = (
                        Ejemplar.objects.filter(pk=object_id)
                        .values("libro_id")
                        .first()
                    )

                    if referencia:
                        list(
                            Libro.objects.select_for_update()
                            .filter(pk=referencia["libro_id"])
                        )

                        list(
                            Ejemplar.objects.select_for_update()
                            .filter(pk=object_id)
                        )

                return super().changeform_view(
                    request,
                    object_id,
                    form_url,
                    extra_context,
                )

        return super().changeform_view(
            request,
            object_id,
            form_url,
            extra_context,
        )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        atender_disponibilidad(obj)


admin.site.register(Categoria)
admin.site.register(Editorial)
admin.site.register(Autor)
admin.site.register(SugerenciaAdquisicion)