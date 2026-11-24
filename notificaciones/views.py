from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Notificacion


@login_required
def mis_notificaciones_view(request):
    avisos = Notificacion.objects.filter(
        usuario=request.user
    ).order_by("-fecha", "-pk")

    pagina = Paginator(avisos, 15).get_page(request.GET.get("page"))

    return render(
        request,
        "notificaciones/mis_notificaciones.html",
        {"pagina": pagina},
    )


@login_required
@require_POST
def marcar_leida_view(request, notificacion_id):
    aviso = get_object_or_404(
        Notificacion,
        pk=notificacion_id,
        usuario=request.user,
    )

    if not aviso.leida:
        aviso.leida = True
        aviso.save(update_fields=["leida"])

    return redirect("mis_notificaciones")