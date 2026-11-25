from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Exists, OuterRef

from .models import Libro, Categoria, SugerenciaAdquisicion, Ejemplar
from cuentas.models import Profesor, Departamento

from django.core.paginator import Paginator
from .models import LibroAutor
# Vista principal del catálogo
@login_required
def catalogo_view(request):
    """Busca libros activos y muestra 12 resultados por página."""
    query = request.GET.get("q", "").strip()
    categoria_id = request.GET.get("categoria", "").strip()

    categorias = list(
        Categoria.objects.order_by("nombre", "pk")
    )

    libros = Libro.objects.filter(activo=True)

    if query:
        libros = libros.filter(
            Q(titulo__icontains=query)
            | Q(isbn__icontains=query)
            | Q(autores__nombre__icontains=query)
            | Q(autores__apellidos__icontains=query)
            | Q(editorial__nombre__icontains=query)
            | Q(categoria__nombre__icontains=query)
        ).distinct()

    if categoria_id:
        categorias_validas = {
            str(categoria.pk) for categoria in categorias
        }

        if categoria_id in categorias_validas:
            libros = libros.filter(categoria_id=categoria_id)
        else:
            libros = libros.none()

    libros = libros.order_by("titulo", "pk")

    # Primero contamos y seleccionamos solo los IDs de esta página.
    pagina = Paginator(
        libros.values_list("pk", flat=True),
        12,
    ).get_page(request.GET.get("pagina"))

    ids_pagina = list(pagina.object_list)

    # Cargamos las relaciones únicamente de esos libros.
    libros_pagina = list(
        Libro.objects.filter(pk__in=ids_pagina)
        .select_related("categoria", "editorial")
        .prefetch_related("autores")
    )

    libros_por_id = {
        libro.pk: libro for libro in libros_pagina
    }

    estados = (
        Ejemplar.objects.filter(libro_id__in=ids_pagina)
        .order_by()
        .values_list("libro_id", "estado")
        .distinct()
    )

    disponibles = set()
    reservables = set()

    for libro_id, estado in estados:
        if estado == "DISPONIBLE":
            disponibles.add(libro_id)
        elif estado in {
            "PRESTADO",
            "RESERVADO",
            "EN_REPARACION",
        }:
            reservables.add(libro_id)

    resultado = []

    for libro_id in ids_pagina:
        libro = libros_por_id.get(libro_id)

        if libro is not None:
            libro.tiene_disponibles = libro_id in disponibles
            libro.permite_reserva = libro_id in reservables
            resultado.append(libro)

    pagina.object_list = resultado

    parametros = request.GET.copy()
    parametros.pop("pagina", None)

    return render(
        request,
        "catalogo/catalogo.html",
        {
            "libros": pagina,
            "pagina": pagina,
            "categorias": categorias,
            "query": query,
            "categoria_id": categoria_id,
            "filtros_url": parametros.urlencode(),
        },
    )
# Sugerencias de adquisición del profesor (CU-16)
@login_required
def sugerir_adquisicion_view(request):
    """Permite a los docentes sugerir la adquisición de libros."""

    if request.user.tipo_usuario != "PROFESOR":
        messages.error(request, "Solo profesores pueden enviar sugerencias.")
        return redirect("catalogo")

    if request.method == "POST":
        titulo = request.POST.get("titulo")
        autores = request.POST.get("autores")
        isbn = request.POST.get("isbn", "")
        justificacion = request.POST.get("justificacion")

        # Departamento por defecto
        depto, _ = Departamento.objects.get_or_create(
            nombre="General"
        )

        # Crear el perfil del profesor si todavía no existe
        profesor_perfil, _ = Profesor.objects.get_or_create(
            usuario=request.user,
            defaults={
                "num_empleado": f"EMP-{request.user.id}",
                "departamento": depto,
            },
        )

        SugerenciaAdquisicion.objects.create(
            profesor=request.user,
            titulo=titulo,
            autores=autores,
            isbn=isbn,
            justificacion=justificacion,
            estado="PENDIENTE",
        )

        messages.success(
            request,
            "¡Tu sugerencia de libro ha sido enviada "
            "con éxito al bibliotecario!",
        )

        return redirect("catalogo")

    return render(request, "catalogo/sugerir_adquisicion.html")


# Consulta de sugerencias para el bibliotecario (CU-33)
@login_required
def lista_sugerencias_view(request):
    """Muestra todas las sugerencias al bibliotecario."""

    if request.user.tipo_usuario != "BIBLIOTECARIO":
        messages.error(request, "Acceso exclusivo para el bibliotecario.")
        return redirect("catalogo")

    sugerencias = SugerenciaAdquisicion.objects.all().order_by("-fecha")

    return render(
        request,
        "catalogo/lista_sugerencias.html",
        {"sugerencias": sugerencias},
    )


# Aprobar o rechazar una sugerencia
@login_required
def cambiar_estado_sugerencia(request, sugerencia_id, nuevo_estado):
    """Cambia el estado de la sugerencia a APROBADA o RECHAZADA."""

    if request.user.tipo_usuario != "BIBLIOTECARIO":
        messages.error(request, "Acceso no autorizado.")
        return redirect("catalogo")

    if nuevo_estado not in ["APROBADA", "RECHAZADA"]:
        messages.error(request, "Estado no válido.")
        return redirect("lista_sugerencias")

    sugerencia = get_object_or_404(
        SugerenciaAdquisicion,
        id=sugerencia_id,
    )

    sugerencia.estado = nuevo_estado
    sugerencia.save()

    if nuevo_estado == "APROBADA":
        messages.success(
            request,
            f"La sugerencia '{sugerencia.titulo}' ha sido APROBADA.",
        )
    else:
        messages.info(
            request,
            f"La sugerencia '{sugerencia.titulo}' ha sido RECHAZADA.",
        )

    return redirect("lista_sugerencias")
@login_required
def detalle_libro_view(request, libro_id):
    from django.core.paginator import Paginator
    from .models import LibroAutor

    # El detalle solo consulta información.
    if request.method != "GET":
        from django.http import HttpResponseNotAllowed

        return HttpResponseNotAllowed(["GET"])

    libros = Libro.objects.select_related(
        "categoria",
        "editorial",
    )

    # Los lectores solo pueden consultar libros activos.
    if request.user.tipo_usuario != "BIBLIOTECARIO":
        libros = libros.filter(activo=True)

    libro = get_object_or_404(libros, pk=libro_id)

    autorias = (
        LibroAutor.objects.filter(libro=libro)
        .select_related("autor")
        .order_by("orden", "pk")
    )

    ejemplares = libro.ejemplares.order_by("codigo_inventario", "pk")

    disponibles = ejemplares.filter(
        estado="DISPONIBLE",
    ).count()

    permite_reserva = (
        libro.activo
        and disponibles == 0
        and ejemplares.filter(
            estado__in=["PRESTADO", "RESERVADO", "EN_REPARACION"],
        ).exists()
    )

    pagina = Paginator(ejemplares, 15).get_page(
        request.GET.get("pagina")
    )

    return render(
        request,
        "catalogo/detalle_libro.html",
        {
            "libro": libro,
            "autorias": autorias,
            "pagina_ejemplares": pagina,
            "total_ejemplares": pagina.paginator.count,
            "disponibles": disponibles,
            "permite_reserva": permite_reserva,
        },
    )