from decimal import Decimal
from django.views.decorators.http import require_POST
from cuentas.models import Usuario
from django.shortcuts import render, redirect, get_object_or_404 
from django.contrib.auth.decorators import login_required 
from django.contrib import messages 
from django.utils import timezone 
from datetime import timedelta 
from django.db import transaction
from .models import Prestamo, PoliticaPrestamo, Reserva
from catalogo.models import Libro, Ejemplar
from multas.models import Multa
from notificaciones.models import Notificacion

# solicitar prestamo en linea -- cu-06 / cu-23 / rn-01 / rn_08
@login_required
def solicitar_prestamo_view(request, libro_id):
    """Permite al usuario solicitar un libro disponible desde el catálogo."""
    libro = get_object_or_404(Libro, pk=libro_id)
    
    #valida elegibilidad del usuario (sin multas pendientes ni vencidas)
    puede_pedir, mensaje_error = request.user.puede_solicitar_prestamos()
    if not puede_pedir:
        messages.error(request, mensaje_error)
        return redirect('catalogo')
    
    #busca ejemplar disponible en estante
    ejemplar = Ejemplar.objects.filter(libro=libro, estado='DISPONIBLE').first()
    if not ejemplar:
        messages.warning(request, f"No hay ejemplares disponibles de '{libro.titulo}'.")
        return redirect('catalogo')
    
    politica = PoliticaPrestamo.objects.filter(
    tipo_usuario=request.user.tipo_usuario
    ).first()
    horas_tol = politica.horas_para_recoger if politica else 48
    fecha_ahora = timezone.now()
    
    #TODO: INVESTIGAR PARA QUE SIRVE ESTO
    with transaction.atomic():
        prestamo = Prestamo.objects.create(
            usuario=request.user,
            ejemplar=ejemplar,
            fecha_solicitud=fecha_ahora,
            fecha_limite_recoger=fecha_ahora + timedelta(hours=horas_tol)
        )
        ejemplar.estado = 'RESERVADO'
        ejemplar.save()
        
    messages.success(
        request,
        f"Solicitud # {prestamo.id} registrada. Tienes hasta {prestamo.fecha_limite_recoger.strftime('%d/%m/%Y %H:%M')} para recogerlo en mostrador."
    )
    return redirect('mis_prestamos')

#entregar en mostrador cu-24 --> solo bibliotecario
@login_required
@require_POST
def entregar_prestamo_view(request, prestamo_id):
    """Registra la entrega del ejemplar al usuario."""
    if request.user.tipo_usuario != 'BIBLIOTECARIO':
        messages.error(request, 'Acceso no autorizado.')
        return redirect('home')

    solicitud = get_object_or_404(Prestamo, pk=prestamo_id)

    with transaction.atomic():
        # Bloqueamos los registros mientras se procesa la entrega.
        usuario = Usuario.objects.select_for_update().get(
            pk=solicitud.usuario_id
        )
        prestamo = Prestamo.objects.select_for_update().get(
            pk=prestamo_id
        )
        ejemplar = Ejemplar.objects.select_for_update().get(
            pk=prestamo.ejemplar_id
        )

        if prestamo.estado != 'SOLICITADO':
            messages.error(request, 'Esta solicitud ya no está pendiente de entrega.')
            return redirect('home')

        ahora = timezone.now()

        if (
            prestamo.fecha_limite_recoger
            and ahora >= prestamo.fecha_limite_recoger
        ):
            messages.error(request, 'El plazo para recoger esta solicitud terminó.')
            return redirect('home')

        if usuario.bloqueado:
            messages.error(
                request,
                f'Cuenta suspendida: {usuario.motivo_bloqueo or "Consulta en biblioteca."}'
            )
            return redirect('home')

        if usuario.tiene_multas_pendientes() or usuario.tiene_prestamos_vencidos():
            messages.error(request, 'El usuario tiene multas pendientes o préstamos vencidos.')
            return redirect('home')

        if ejemplar.estado != 'RESERVADO':
            messages.error(request, 'El ejemplar no está reservado para la entrega.')
            return redirect('home')

        politica = PoliticaPrestamo.objects.filter(
            tipo_usuario=usuario.tipo_usuario
        ).first()

        dias_por_tipo = {
            'ESTUDIANTE': 7,
            'PROFESOR': 30,
        }

        if usuario.tipo_usuario not in dias_por_tipo:
            messages.error(request, 'El usuario no tiene un tipo de lector válido.')
            return redirect('home')

        dias = (
            politica.dias_prestamos
            if politica
            else dias_por_tipo[usuario.tipo_usuario]
        )

        prestamo.estado = 'ACTIVO'
        prestamo.fecha_prestamo = ahora
        prestamo.fecha_vencimiento = (
            timezone.localdate(ahora) + timedelta(days=dias)
        )
        prestamo.entregado_por = request.user
        prestamo.save(update_fields=[
            'estado',
            'fecha_prestamo',
            'fecha_vencimiento',
            'entregado_por',
        ])

        ejemplar.estado = 'PRESTADO'
        ejemplar.save(update_fields=['estado'])

    messages.success(
        request,
        f'Préstamo #{prestamo.id} entregado. '
        f'Vence el {prestamo.fecha_vencimiento:%d/%m/%Y}.'
    )
    return redirect('home')

#devolver en mostrador cu-25 / rn-04 / rn_07 / rn_12  (solo bibiliotecario)
@login_required
@require_POST
def devolver_prestamo_view(request, prestamo_id):
    """Registra la devolución y calcula la multa si hubo retraso."""
    if request.user.tipo_usuario != 'BIBLIOTECARIO':
        messages.error(request, 'Acceso no autorizado.')
        return redirect('home')

    solicitud = get_object_or_404(Prestamo, pk=prestamo_id)

    with transaction.atomic():
        usuario = Usuario.objects.select_for_update().get(
            pk=solicitud.usuario_id
        )
        prestamo = Prestamo.objects.select_for_update().get(
            pk=prestamo_id
        )
        ejemplar = Ejemplar.objects.select_for_update().get(
            pk=prestamo.ejemplar_id
        )

        if prestamo.estado not in ['ACTIVO', 'VENCIDO']:
            messages.error(
                request,
                'Este préstamo no está pendiente de devolución.'
            )
            return redirect('home')

        if not prestamo.fecha_vencimiento:
            messages.error(
                request,
                'El préstamo no tiene fecha de vencimiento. '
                'Revisa el registro antes de devolverlo.'
            )
            return redirect('home')

        if ejemplar.estado != 'PRESTADO':
            messages.error(
                request,
                'El estado del ejemplar no coincide con el préstamo. '
                'Revisa el registro antes de continuar.'
            )
            return redirect('home')

        ahora = timezone.now()
        hoy = timezone.localdate(ahora)
        dias_retraso = max(
            (hoy - prestamo.fecha_vencimiento).days,
            0
        )

        politica = PoliticaPrestamo.objects.filter(
            tipo_usuario=usuario.tipo_usuario
        ).first()

        tarifa = (
            politica.multa_por_dia
            if politica
            else Decimal('10.00')
        )
        tope = (
            politica.multa_maxima
            if politica
            else Decimal('300.00')
        )

        monto = min(dias_retraso * tarifa, tope)

        if dias_retraso > 0 and monto > 0:
            Multa.objects.get_or_create(
                prestamo=prestamo,
                motivo='RETRASO',
                defaults={
                    'usuario': usuario,
                    'dias_retraso': dias_retraso,
                    'monto': monto,
                    'estado': 'PENDIENTE',
                }
            )

        prestamo.estado = 'DEVUELTO'
        prestamo.fecha_devolucion = ahora
        prestamo.recibido_por = request.user
        prestamo.save(update_fields=[
            'estado',
            'fecha_devolucion',
            'recibido_por',
        ])

        # Asigna por orden FIFO y genera el aviso al lector.
        reserva = asignar_reserva_o_liberar(ejemplar, ahora)

    if dias_retraso > 0 and monto > 0:
        messages.warning(
            request,
            f'Préstamo #{prestamo.id} devuelto con '
            f'{dias_retraso} días de retraso. '
            f'Multa por retraso: ${monto:.2f} MXN.'
        )
    else:
        messages.success(
            request,
            f'Préstamo #{prestamo.id} devuelto sin multa por retraso.'
        )

    if reserva:
        messages.info(
            request,
            'El ejemplar quedó reservado para el siguiente lector de la cola.'
        )

    return redirect('home')
@login_required
def devoluciones_pendientes_view(request):
    """Muestra los préstamos pendientes de devolución."""
    if request.user.tipo_usuario != 'BIBLIOTECARIO':
        messages.error(request, 'Acceso no autorizado.')
        return redirect('home')

    prestamos = Prestamo.objects.filter(
        estado__in=['ACTIVO', 'VENCIDO']
    ).select_related(
        'usuario',
        'ejemplar__libro'
    ).order_by('fecha_vencimiento', 'pk')

    return render(
        request,
        'prestamos/devoluciones_pendientes.html',
        {
            'prestamos': prestamos,
            'hoy': timezone.localdate(),
        }
    )
@login_required
def mis_prestamos_view(request):
    """Muestra los préstamos del usuario que inició sesión."""
    prestamos = Prestamo.objects.filter(
        usuario=request.user
    ).select_related(
        'ejemplar__libro'
    ).order_by('-fecha_solicitud', '-pk')

    return render(
        request,
        'prestamos/mis_prestamos.html',
        {'prestamos': prestamos}
    )
@login_required
def solicitudes_pendientes_view(request):
    """Muestra las solicitudes pendientes de entrega."""
    if request.user.tipo_usuario != 'BIBLIOTECARIO':
        messages.error(request, 'Acceso no autorizado.')
        return redirect('home')

    solicitudes = Prestamo.objects.filter(
        estado='SOLICITADO'
    ).select_related(
        'usuario',
        'ejemplar__libro'
    ).order_by('fecha_solicitud', 'pk')

    return render(
        request,
        'prestamos/solicitudes_pendientes.html',
        {
            'solicitudes': solicitudes,
            'ahora': timezone.now(),
        }
    )
@login_required
@require_POST
def reservar_libro_view(request, libro_id):
    if request.user.tipo_usuario not in ["ESTUDIANTE", "PROFESOR"]:
        messages.error(request, "Solo los lectores pueden reservar libros.")
        return redirect("catalogo")

    with transaction.atomic():
        usuario = Usuario.objects.select_for_update().get(
            pk=request.user.pk
        )

        libro = get_object_or_404(
            Libro.objects.select_for_update(),
            pk=libro_id,
            activo=True,
        )

        puede_reservar, motivo = usuario.puede_solicitar_prestamos()

        if not puede_reservar:
            messages.error(request, motivo)
            return redirect("catalogo")

        # También comprobamos las fechas, aunque el comando
        # todavía no haya cambiado el estado a VENCIDO.
        if Prestamo.objects.filter(
            usuario=usuario,
            estado__in=["ACTIVO", "VENCIDO"],
            fecha_vencimiento__lt=timezone.localdate(),
        ).exists():
            messages.error(
                request,
                "Tienes préstamos vencidos pendientes de devolución.",
            )
            return redirect("catalogo")

        if Prestamo.objects.filter(
            usuario=usuario,
            ejemplar__libro=libro,
            estado__in=["SOLICITADO", "ACTIVO", "VENCIDO"],
        ).exists():
            messages.error(
                request,
                "Ya tienes una solicitud o préstamo vigente de este título.",
            )
            return redirect("catalogo")

        if Reserva.objects.filter(
            usuario=usuario,
            libro=libro,
            estado__in=["PENDIENTE", "DISPONIBLE"],
        ).exists():
            messages.info(
                request,
                "Ya tienes una reserva vigente de este libro.",
            )
            return redirect("mis_reservas")

        if Ejemplar.objects.filter(
            libro=libro,
            estado="DISPONIBLE",
        ).exists():
            messages.info(
                request,
                "Hay ejemplares disponibles. Solicita el préstamo "
                "desde el catálogo.",
            )
            return redirect("catalogo")

        # Evitamos una reserva sin posibilidad de ser atendida
        # cuando todos los ejemplares están retirados.
        if not Ejemplar.objects.filter(
            libro=libro,
            estado__in=["PRESTADO", "RESERVADO", "EN_REPARACION"],
        ).exists():
            messages.error(
                request,
                "Este título no tiene ejemplares habilitados "
                "para una reserva.",
            )
            return redirect("catalogo")

        reserva = Reserva.objects.create(
            usuario=usuario,
            libro=libro,
            estado="PENDIENTE",
        )

    messages.success(
        request,
        f"Reserva #{reserva.pk} registrada. "
        "Te avisaremos cuando haya un ejemplar disponible.",
    )
    return redirect("mis_reservas")


@login_required
def mis_reservas_view(request):
    if request.user.tipo_usuario not in ["ESTUDIANTE", "PROFESOR"]:
        messages.error(request, "Esta sección corresponde a los lectores.")
        return redirect("home")

    reservas = (
        Reserva.objects.filter(usuario=request.user)
        .select_related("libro", "ejemplar_asignado")
        .order_by("-fecha_reserva", "-pk")
    )

    return render(
        request,
        "prestamos/mis_reservas.html",
        {"reservas": reservas},
    )
def asignar_reserva_o_liberar(ejemplar, ahora):
    """Se usa dentro de una transacción con el ejemplar bloqueado."""

    # No liberamos un ejemplar que tenga otro préstamo vigente.
    if Prestamo.objects.filter(
        ejemplar=ejemplar,
        estado__in=["SOLICITADO", "ACTIVO", "VENCIDO"],
    ).exists():
        return None

    if Reserva.objects.filter(
        ejemplar_asignado=ejemplar,
        estado="DISPONIBLE",
    ).exists():
        return None

    siguiente = (
        Reserva.objects.select_for_update()
        .filter(
            libro_id=ejemplar.libro_id,
            estado="PENDIENTE",
        )
        .order_by("fecha_reserva", "pk")
        .first()
    )

    if siguiente:
        politica = PoliticaPrestamo.objects.filter(
            tipo_usuario=siguiente.usuario.tipo_usuario
        ).first()

        horas = politica.horas_para_recoger if politica else 48

        siguiente.estado = "DISPONIBLE"
        siguiente.ejemplar_asignado = ejemplar
        siguiente.fecha_expiracion = ahora + timedelta(hours=horas)
        siguiente.save(update_fields=[
            "estado",
            "ejemplar_asignado",
            "fecha_expiracion",
        ])

        ejemplar.estado = "RESERVADO"

        Notificacion.objects.get_or_create(
            usuario=siguiente.usuario,
            tipo="RESERVA_DISPONIBLE",
            mensaje=(
                f"Reserva #{siguiente.pk}: tu ejemplar "
                f"{ejemplar.codigo_inventario} está disponible. "
                f"Tienes {horas} horas para recogerlo."
            ),
        )
    else:
        ejemplar.estado = "DISPONIBLE"

    ejemplar.save(update_fields=["estado"])
    return siguiente


@login_required
@require_POST
def cancelar_reserva_view(request, reserva_id):
    datos = get_object_or_404(
        Reserva,
        pk=reserva_id,
        usuario=request.user,
    )

    with transaction.atomic():
        Usuario.objects.select_for_update().get(pk=request.user.pk)

        ejemplar = None
        if datos.ejemplar_asignado_id:
            ejemplar = Ejemplar.objects.select_for_update().get(
                pk=datos.ejemplar_asignado_id
            )

        reserva = get_object_or_404(
            Reserva.objects.select_for_update(),
            pk=reserva_id,
            usuario=request.user,
        )

        if reserva.estado not in ["PENDIENTE", "DISPONIBLE"]:
            messages.error(
                request,
                "Esta reserva ya no se puede cancelar.",
            )
            return redirect("mis_reservas")

        if reserva.ejemplar_asignado_id != datos.ejemplar_asignado_id:
            messages.info(
                request,
                "La reserva cambió. Actualiza la página e inténtalo otra vez.",
            )
            return redirect("mis_reservas")

        estaba_disponible = reserva.estado == "DISPONIBLE"

        reserva.estado = "CANCELADA"
        reserva.save(update_fields=["estado"])

        if estaba_disponible and ejemplar:
            if ejemplar.estado == "RESERVADO":
                asignar_reserva_o_liberar(ejemplar, timezone.now())

    messages.success(request, f"Reserva #{reserva.pk} cancelada.")
    return redirect("mis_reservas")


@login_required
def reservas_para_entregar_view(request):
    if request.user.tipo_usuario != "BIBLIOTECARIO":
        messages.error(request, "Acceso exclusivo para el bibliotecario.")
        return redirect("home")

    reservas = (
        Reserva.objects.filter(estado="DISPONIBLE")
        .select_related("usuario", "libro", "ejemplar_asignado")
        .order_by("fecha_expiracion", "pk")
    )

    return render(
        request,
        "prestamos/reservas_para_entregar.html",
        {"reservas": reservas},
    )


@login_required
@require_POST
def recoger_reserva_view(request, reserva_id):
    if request.user.tipo_usuario != "BIBLIOTECARIO":
        messages.error(request, "Acceso no autorizado.")
        return redirect("home")

    datos = get_object_or_404(Reserva, pk=reserva_id)

    with transaction.atomic():
        usuario = Usuario.objects.select_for_update().get(
            pk=datos.usuario_id
        )

        ejemplar = None
        if datos.ejemplar_asignado_id:
            ejemplar = Ejemplar.objects.select_for_update().get(
                pk=datos.ejemplar_asignado_id
            )

        reserva = Reserva.objects.select_for_update().get(pk=reserva_id)
        ahora = timezone.now()
        hoy = timezone.localdate(ahora)

        if reserva.estado != "DISPONIBLE":
            messages.error(request, "La reserva ya no está disponible.")
            return redirect("reservas_para_entregar")

        if (
            not ejemplar
            or reserva.ejemplar_asignado_id != ejemplar.pk
            or ejemplar.libro_id != reserva.libro_id
            or ejemplar.estado != "RESERVADO"
        ):
            messages.error(
                request,
                "El ejemplar asignado no coincide con la reserva.",
            )
            return redirect("reservas_para_entregar")

        if not reserva.fecha_expiracion:
            messages.error(request, "La reserva no tiene plazo de recogida.")
            return redirect("reservas_para_entregar")

        if reserva.fecha_expiracion <= ahora:
            reserva.estado = "EXPIRADA"
            reserva.save(update_fields=["estado"])
            asignar_reserva_o_liberar(ejemplar, ahora)

            messages.warning(request, "El plazo de recogida ya terminó.")
            return redirect("reservas_para_entregar")

        if usuario.tipo_usuario not in ["ESTUDIANTE", "PROFESOR"]:
            messages.error(request, "La cuenta no corresponde a un lector.")
            return redirect("reservas_para_entregar")

        puede_pedir, motivo = usuario.puede_solicitar_prestamos()
        if not puede_pedir:
            messages.error(request, motivo)
            return redirect("reservas_para_entregar")

        if Prestamo.objects.filter(
            usuario=usuario,
            estado__in=["ACTIVO", "VENCIDO"],
            fecha_vencimiento__lt=hoy,
        ).exists():
            messages.error(request, "El lector tiene préstamos vencidos.")
            return redirect("reservas_para_entregar")

        if not reserva.libro.activo:
            messages.error(request, "El libro está dado de baja.")
            return redirect("reservas_para_entregar")

        if Prestamo.objects.filter(
            usuario=usuario,
            ejemplar__libro_id=reserva.libro_id,
            estado__in=["SOLICITADO", "ACTIVO", "VENCIDO"],
        ).exists():
            messages.error(
                request,
                "El lector ya tiene una solicitud o préstamo de este título.",
            )
            return redirect("reservas_para_entregar")

        if Prestamo.objects.filter(
            ejemplar=ejemplar,
            estado__in=["SOLICITADO", "ACTIVO", "VENCIDO"],
        ).exists():
            messages.error(request, "El ejemplar ya tiene un préstamo vigente.")
            return redirect("reservas_para_entregar")

        if Reserva.objects.filter(
            ejemplar_asignado=ejemplar,
            estado="DISPONIBLE",
        ).exclude(pk=reserva.pk).exists():
            messages.error(
                request,
                "El ejemplar también aparece asignado a otra reserva.",
            )
            return redirect("reservas_para_entregar")

        politica = PoliticaPrestamo.objects.filter(
            tipo_usuario=usuario.tipo_usuario
        ).first()

        es_estudiante = usuario.tipo_usuario == "ESTUDIANTE"
        dias = politica.dias_prestamos if politica else (
            7 if es_estudiante else 30
        )
        limite = politica.max_libros if politica else (
            3 if es_estudiante else 10
        )

        if usuario.total_prestamos_activos() >= limite:
            messages.error(
                request,
                f"El lector alcanzó el límite de {limite} libros.",
            )
            return redirect("reservas_para_entregar")

        prestamo = Prestamo.objects.create(
            usuario=usuario,
            ejemplar=ejemplar,
            estado="ACTIVO",
            fecha_solicitud=reserva.fecha_reserva,
            fecha_prestamo=ahora,
            fecha_vencimiento=hoy + timedelta(days=dias),
            entregado_por=request.user,
            observaciones=f"Recogida de reserva #{reserva.pk}.",
        )

        reserva.estado = "ATENDIDA"
        reserva.save(update_fields=["estado"])

        ejemplar.estado = "PRESTADO"
        ejemplar.save(update_fields=["estado"])

    messages.success(
        request,
        f"Reserva #{reserva.pk} entregada. "
        f"Préstamo #{prestamo.pk} activo hasta "
        f"{prestamo.fecha_vencimiento:%d/%m/%Y}.",
    )
    return redirect("reservas_para_entregar")