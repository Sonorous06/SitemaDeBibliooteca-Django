from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Exists, OuterRef

from .models import Libro, Categoria, SugerenciaAdquisicion, Ejemplar
from cuentas.models import Profesor, Departamento


# Vista principal del catálogo
@login_required
def catalogo_view(request):
    """Busca libros activos y muestra su disponibilidad."""

    query = request.GET.get("q", "").strip()
    categoria_id = request.GET.get("categoria", "")

    # Libros activos
    libros = Libro.objects.filter(activo=True)

    # Búsqueda por título, ISBN, autor o editorial
    if query:
        libros = libros.filter(
            Q(titulo__icontains=query)
            | Q(isbn__icontains=query)
            | Q(autores__nombre__icontains=query)
            | Q(autores__apellidos__icontains=query)
            | Q(editorial__nombre__icontains=query)
        ).distinct()

    if categoria_id:
        libros = libros.filter(categoria_id=categoria_id)

    categorias = Categoria.objects.all()

    # Disponibilidad para préstamo o reserva
    libros = libros.annotate(
        tiene_disponibles=Exists(
            Ejemplar.objects.filter(
                libro_id=OuterRef("pk"),
                estado="DISPONIBLE",
            )
        ),
        permite_reserva=Exists(
            Ejemplar.objects.filter(
                libro_id=OuterRef("pk"),
                estado__in=[
                    "PRESTADO",
                    "RESERVADO",
                    "EN_REPARACION",
                ],
            )
        ),
    )

    context = {
        "libros": libros,
        "categorias": categorias,
        "query": query,
        "categoria_id": categoria_id,
    }

    return render(request, "catalogo/catalogo.html", context)


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