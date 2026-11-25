from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render

from .forms_lectores import LectorForm, guardar_lector


Usuario = get_user_model()


def _formulario_lector(request, usuario_id=None):
    if request.user.tipo_usuario != "BIBLIOTECARIO":
        messages.error(request, "Acceso exclusivo para el bibliotecario.")
        return redirect("home")

    if request.method not in ("GET", "POST"):
        return HttpResponseNotAllowed(["GET", "POST"])

    editando = usuario_id is not None

    try:
        with transaction.atomic():
            instancia = None

            if editando:
                lectores = Usuario.objects.filter(
                    tipo_usuario__in=["ESTUDIANTE", "PROFESOR"],
                    is_staff=False,
                    is_superuser=False,
                )

                if request.method == "POST":
                    lectores = lectores.select_for_update()

                instancia = get_object_or_404(
                    lectores,
                    pk=usuario_id,
                )

            form = LectorForm(
                data=request.POST if request.method == "POST" else None,
                instance=instancia,
            )

            if request.method == "POST" and form.is_valid():
                lector = guardar_lector(form)

                messages.success(
                    request,
                    f"Lector {lector.username} "
                    f"{'actualizado' if editando else 'creado'} correctamente.",
                )

                return redirect("lista_usuarios")

    except IntegrityError:
        # La transacción revierte también la cuenta si falla su perfil.
        form.add_error(
            None,
            "No se pudo guardar porque algún dato único ya está registrado. "
            "Revisa usuario, correo, matrícula y número de empleado.",
        )

    return render(
        request,
        "cuentas/formulario_lector.html",
        {
            "form": form,
            "editando": editando,
        },
    )


@login_required
def crear_lector_view(request):
    return _formulario_lector(request)


@login_required
def editar_lector_view(request, usuario_id):
    return _formulario_lector(request, usuario_id=usuario_id)