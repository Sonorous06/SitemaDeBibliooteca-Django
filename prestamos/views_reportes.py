from datetime import datetime, time
from decimal import Decimal

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Sum
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET

from multas.models import Multa, Pago
from prestamos.models import Prestamo


class FiltroReportesForm(forms.Form):
    desde = forms.DateField(
        label="Desde",
        input_formats=["%Y-%m-%d"],
        widget=forms.DateInput(
            format="%Y-%m-%d",
            attrs={
                "type": "date",
                "class": (
                    "w-full px-4 py-3 rounded-lg "
                    "border border-line bg-cream text-coffee"
                ),
            },
        ),
    )

    hasta = forms.DateField(
        label="Hasta",
        input_formats=["%Y-%m-%d"],
        widget=forms.DateInput(
            format="%Y-%m-%d",
            attrs={
                "type": "date",
                "class": (
                    "w-full px-4 py-3 rounded-lg "
                    "border border-line bg-cream text-coffee"
                ),
            },
        ),
    )

    def clean(self):
        datos = super().clean()
        desde = datos.get("desde")
        hasta = datos.get("hasta")

        if desde and hasta and desde > hasta:
            raise forms.ValidationError(
                "La fecha inicial no puede ser posterior a la fecha final."
            )

        return datos


@login_required
@require_GET
def reportes_biblioteca_view(request):
    if request.user.tipo_usuario != "BIBLIOTECARIO":
        messages.error(request, "Acceso exclusivo para el bibliotecario.")
        return redirect("home")

    hoy = timezone.localdate()

    datos = {
        "desde": request.GET.get(
            "desde",
            hoy.replace(day=1).isoformat(),
        ),
        "hasta": request.GET.get("hasta", hoy.isoformat()),
    }

    form = FiltroReportesForm(datos)
    context = {"form": form, "hoy": hoy}

    if not form.is_valid():
        return render(
            request,
            "prestamos/reportes_biblioteca.html",
            context,
        )

    desde = form.cleaned_data["desde"]
    hasta = form.cleaned_data["hasta"]

    # Incluir ambos días completos en la zona horaria del proyecto.
    zona = timezone.get_current_timezone()

    inicio = timezone.make_aware(
        datetime.combine(desde, time.min),
        zona,
    )
    fin = timezone.make_aware(
        datetime.combine(hasta, time.max),
        zona,
    )

    entregados = Prestamo.objects.filter(
        fecha_prestamo__gte=inicio,
        fecha_prestamo__lte=fin,
    )

    libros_mas_prestados = (
        entregados.values(
            "ejemplar__libro_id",
            "ejemplar__libro__titulo",
        )
        .annotate(total=Count("pk"))
        .order_by("-total", "ejemplar__libro__titulo", "ejemplar__libro_id")[:10]
    )

    # Estado actual: incluir activos atrasados aunque aún no se ejecute
    # el comando que los marca como VENCIDO.
    vencidos = Prestamo.objects.filter(
        estado__in=["ACTIVO", "VENCIDO"],
        fecha_vencimiento__lt=hoy,
    )

    # El dinero cobrado se obtiene de Pago, usando su fecha de pago.
    pagos_periodo = Pago.objects.filter(
        fecha_pago__gte=inicio,
        fecha_pago__lte=fin,
    )

    cobrado = pagos_periodo.aggregate(
        total=Sum("monto"),
    )["total"] or Decimal("0.00")

    pendientes = Multa.objects.filter(estado="PENDIENTE")

    saldo_pendiente = pendientes.aggregate(
        total=Sum("monto"),
    )["total"] or Decimal("0.00")

    pendientes_por_motivo = list(
        pendientes.values("motivo")
        .annotate(cantidad=Count("pk"), total=Sum("monto"))
        .order_by("motivo")
    )

    etiquetas = dict(Multa.MOTIVOS)

    for fila in pendientes_por_motivo:
        fila["nombre"] = etiquetas.get(fila["motivo"], fila["motivo"])

    pagina_entregados = Paginator(
        entregados.select_related(
            "usuario",
            "ejemplar__libro",
            "entregado_por",
        ).order_by("-fecha_prestamo", "-pk"),
        15,
    ).get_page(request.GET.get("pagina_entregados"))

    pagina_vencidos = Paginator(
        vencidos.select_related(
            "usuario",
            "ejemplar__libro",
        ).order_by("fecha_vencimiento", "pk"),
        15,
    ).get_page(request.GET.get("pagina_vencidos"))

    # Conservar filtros y la página de la otra tabla al navegar.
    parametros_entregados = request.GET.copy()
    parametros_entregados["desde"] = desde.isoformat()
    parametros_entregados["hasta"] = hasta.isoformat()
    parametros_entregados.pop("pagina_entregados", None)

    parametros_vencidos = request.GET.copy()
    parametros_vencidos["desde"] = desde.isoformat()
    parametros_vencidos["hasta"] = hasta.isoformat()
    parametros_vencidos.pop("pagina_vencidos", None)

    context.update(
        {
            "reportes_validos": True,
            "desde": desde,
            "hasta": hasta,
            "total_entregados": pagina_entregados.paginator.count,
            "total_vencidos": pagina_vencidos.paginator.count,
            "cobrado": cobrado,
            "cantidad_pagos": pagos_periodo.count(),
            "saldo_pendiente": saldo_pendiente,
            "cantidad_multas_pendientes": pendientes.count(),
            "pendientes_por_motivo": pendientes_por_motivo,
            "libros_mas_prestados": libros_mas_prestados,
            "pagina_entregados": pagina_entregados,
            "pagina_vencidos": pagina_vencidos,
            "parametros_entregados": parametros_entregados.urlencode(),
            "parametros_vencidos": parametros_vencidos.urlencode(),
        }
    )

    return render(
        request,
        "prestamos/reportes_biblioteca.html",
        context,
    )