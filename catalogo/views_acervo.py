from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.db.models.deletion import ProtectedError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import (
    require_GET,
    require_http_methods,
    require_POST,
)

from .forms_acervo import (
    AutorAcervoForm,
    CategoriaAcervoForm,
    EditorialAcervoForm,
    EjemplarAcervoForm,
    LibroAcervoForm,
)
from .models import Autor, Categoria, Editorial, Ejemplar, Libro, LibroAutor


def bibliotecario_required(vista):
    @login_required
    @wraps(vista)
    def protegida(request, *args, **kwargs):
        if request.user.tipo_usuario != "BIBLIOTECARIO":
            messages.error(request, "Acceso exclusivo para el bibliotecario.")
            return redirect("catalogo")
        return vista(request, *args, **kwargs)

    return protegida


def paginar(request, consulta):
    pagina = Paginator(consulta, 15).get_page(request.GET.get("pagina"))
    parametros = request.GET.copy()
    parametros.pop("pagina", None)
    return {"pagina": pagina, "filtros_url": parametros.urlencode()}


@bibliotecario_required
@require_GET
def lista_acervo_view(request):
    consulta = Libro.objects.select_related("categoria", "editorial")
    query = request.GET.get("q", "").strip()
    estado = request.GET.get("estado", "")
    if query:
        consulta = consulta.filter(
            Q(titulo__icontains=query) | Q(isbn__icontains=query)
        )
    if estado in ("activo", "inactivo"):
        consulta = consulta.filter(activo=estado == "activo")
    consulta = consulta.annotate(total_ejemplares=Count("ejemplares"))
    contexto = paginar(request, consulta.order_by("titulo", "pk"))
    contexto.update({"query": query, "estado": estado})
    return render(request, "catalogo/acervo/lista.html", contexto)


def guardar_autores(libro, autores):
    seleccionados = [autor.pk for autor in autores]
    orden_anterior = list(
        LibroAutor.objects.filter(libro=libro)
        .order_by("orden", "pk")
        .values_list("autor_id", flat=True)
    )
    orden = [pk for pk in orden_anterior if pk in seleccionados]
    orden.extend(pk for pk in seleccionados if pk not in orden)
    LibroAutor.objects.filter(libro=libro).exclude(
        autor_id__in=seleccionados
    ).delete()
    for posicion, autor_id in enumerate(orden, start=1):
        LibroAutor.objects.update_or_create(
            libro=libro, autor_id=autor_id, defaults={"orden": posicion}
        )


@bibliotecario_required
@require_http_methods(["GET", "POST"])
def formulario_libro_view(request, libro_id=None):
    libro = get_object_or_404(Libro, pk=libro_id) if libro_id else Libro()
    form = LibroAcervoForm(instance=libro)
    if request.method == "POST":
        try:
            with transaction.atomic():
                if libro_id:
                    libro = get_object_or_404(
                        Libro.objects.select_for_update(), pk=libro_id
                    )
                form = LibroAcervoForm(
                    request.POST, request.FILES, instance=libro
                )
                if form.is_valid():
                    libro = form.save(commit=False)
                    libro.save()
                    # La relación tiene una tabla intermedia con orden propio.
                    guardar_autores(libro, form.cleaned_data["autores"])
                    messages.success(request, "Libro guardado correctamente.")
                    return redirect("acervo_ejemplares", libro_id=libro.pk)
        except IntegrityError:
            form.add_error(
                None,
                "No se pudo guardar. Revisa el ISBN y los datos relacionados.",
            )
    return render(
        request,
        "catalogo/acervo/formulario.html",
        {
            "form": form,
            "titulo": "Editar libro" if libro_id else "Agregar libro",
            "es_libro": True,
            "libro": libro if libro_id else None,
        },
    )


@bibliotecario_required
@require_GET
def lista_ejemplares_view(request, libro_id):
    libro = get_object_or_404(Libro, pk=libro_id)
    consulta = libro.ejemplares.order_by("codigo_inventario", "pk")
    contexto = paginar(request, consulta)
    contexto["libro"] = libro
    return render(request, "catalogo/acervo/ejemplares.html", contexto)


@bibliotecario_required
@require_http_methods(["GET", "POST"])
def formulario_ejemplar_view(request, libro_id=None, ejemplar_id=None):
    if ejemplar_id:
        ejemplar = get_object_or_404(Ejemplar, pk=ejemplar_id)
        libro = ejemplar.libro
    else:
        libro = get_object_or_404(Libro, pk=libro_id)
        ejemplar = Ejemplar(libro=libro)
    form = EjemplarAcervoForm(instance=ejemplar)
    if request.method == "POST":
        try:
            with transaction.atomic():
                if ejemplar_id:
                    ejemplar = get_object_or_404(
                        Ejemplar.objects.select_for_update(), pk=ejemplar_id
                    )
                form = EjemplarAcervoForm(request.POST, instance=ejemplar)
                if form.is_valid():
                    ejemplar = form.save()
                    if (
                        ejemplar.estado == "DISPONIBLE"
                        and ejemplar.libro.activo
                    ):
                        from prestamos.views import asignar_reserva_o_liberar

                        asignar_reserva_o_liberar(ejemplar, timezone.now())
                    messages.success(
                        request, "Ejemplar guardado correctamente."
                    )
                    return redirect(
                        "acervo_ejemplares", libro_id=ejemplar.libro_id
                    )
        except IntegrityError:
            form.add_error(
                None, "No se pudo guardar. Revisa el código de inventario."
            )
    return render(
        request,
        "catalogo/acervo/formulario.html",
        {
            "form": form,
            "titulo": "Editar ejemplar" if ejemplar_id else "Agregar ejemplar",
            "libro": libro,
        },
    )


AUXILIARES = {
    "autores": (Autor, AutorAcervoForm, "Autores"),
    "categorias": (Categoria, CategoriaAcervoForm, "Categorías"),
    "editoriales": (Editorial, EditorialAcervoForm, "Editoriales"),
}


def auxiliar(tipo):
    if tipo not in AUXILIARES:
        raise Http404("Sección no encontrada.")
    return AUXILIARES[tipo]


@bibliotecario_required
@require_GET
def lista_auxiliar_view(request, tipo):
    modelo, _, titulo = auxiliar(tipo)
    consulta = modelo.objects.order_by("nombre", "pk")
    query = request.GET.get("q", "").strip()
    if query:
        filtro = Q(nombre__icontains=query)
        if tipo == "autores":
            filtro |= Q(apellidos__icontains=query)
        consulta = consulta.filter(filtro)
    contexto = paginar(request, consulta)
    contexto.update({"tipo": tipo, "titulo": titulo, "query": query})
    return render(request, "catalogo/acervo/auxiliares.html", contexto)


@bibliotecario_required
@require_http_methods(["GET", "POST"])
def formulario_auxiliar_view(request, tipo, registro_id=None):
    modelo, clase_form, titulo = auxiliar(tipo)
    registro = (
        get_object_or_404(modelo, pk=registro_id) if registro_id else modelo()
    )
    form = clase_form(instance=registro)
    if request.method == "POST":
        try:
            with transaction.atomic():
                if registro_id:
                    registro = get_object_or_404(
                        modelo.objects.select_for_update(), pk=registro_id
                    )
                form = clase_form(request.POST, instance=registro)
                if form.is_valid():
                    form.save()
                    messages.success(
                        request, "Registro guardado correctamente."
                    )
                    return redirect("acervo_auxiliares", tipo=tipo)
        except IntegrityError:
            form.add_error(None, "Ya existe un registro con esos datos.")
    return render(
        request,
        "catalogo/acervo/formulario.html",
        {
            "form": form,
            "titulo": ("Editar: " if registro_id else "Agregar: ") + titulo,
            "tipo": tipo,
        },
    )


@bibliotecario_required
@require_POST
def eliminar_auxiliar_view(request, tipo, registro_id):
    modelo, _, _ = auxiliar(tipo)
    try:
        with transaction.atomic():
            registro = get_object_or_404(
                modelo.objects.select_for_update(), pk=registro_id
            )
            registro.delete()
        messages.success(request, "Registro eliminado correctamente.")
    except (ProtectedError, IntegrityError):
        messages.error(
            request, "Este registro está asociado a libros y debe conservarse."
        )
    return redirect("acervo_auxiliares", tipo=tipo)
