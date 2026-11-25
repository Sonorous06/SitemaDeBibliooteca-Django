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
@login_required
@require_POST
def renovar_prestamo_view(request, prestamo_id):
    if request.user.tipo_usuario not in ["ESTUDIANTE", "PROFESOR"]:
        messages.error(request, "Solo los lectores pueden renovar préstamos.")
        return redirect("home")

    with transaction.atomic():
        usuario = Usuario.objects.select_for_update().get(
            pk=request.user.pk
        )

        prestamo = get_object_or_404(
            Prestamo.objects.select_for_update(),
            pk=prestamo_id,
            usuario=usuario,
        )

        # Compartimos el bloqueo del libro con la creación de reservas.
        libro = Libro.objects.select_for_update().get(
            pk=prestamo.ejemplar.libro_id
        )

        hoy = timezone.localdate()

        if prestamo.estado != "ACTIVO":
            messages.error(
                request,
                "Solo se pueden renovar préstamos activos.",
            )
            return redirect("mis_prestamos")

        if not prestamo.fecha_vencimiento:
            messages.error(
                request,
                "El préstamo no tiene fecha de vencimiento.",
            )
            return redirect("mis_prestamos")

        if prestamo.fecha_vencimiento < hoy:
            messages.error(
                request,
                "No puedes renovar un préstamo vencido.",
            )
            return redirect("mis_prestamos")

        if usuario.bloqueado:
            messages.error(
                request,
                "Tu cuenta está bloqueada. Consulta al bibliotecario.",
            )
            return redirect("mis_prestamos")

        if usuario.tiene_multas_pendientes():
            messages.error(
                request,
                "No puedes renovar mientras tengas multas pendientes.",
            )
            return redirect("mis_prestamos")

        if (
            usuario.tiene_prestamos_vencidos()
            or Prestamo.objects.filter(
                usuario=usuario,
                estado="ACTIVO",
                fecha_vencimiento__lt=hoy,
            ).exists()
        ):
            messages.error(
                request,
                "Tienes préstamos vencidos pendientes de devolución.",
            )
            return redirect("mis_prestamos")

        if not libro.activo:
            messages.error(
                request,
                "Este libro está dado de baja y no permite renovaciones.",
            )
            return redirect("mis_prestamos")

        politica = PoliticaPrestamo.objects.filter(
            tipo_usuario=usuario.tipo_usuario
        ).first()

        es_estudiante = usuario.tipo_usuario == "ESTUDIANTE"

        max_renovaciones = (
            politica.max_renovaciones
            if politica
            else (1 if es_estudiante else 2)
        )

        dias = (
            politica.dias_prestamos
            if politica
            else (7 if es_estudiante else 30)
        )

        if prestamo.num_renovaciones >= max_renovaciones:
            messages.error(
                request,
                f"Alcanzaste el límite de "
                f"{max_renovaciones} renovaciones para este préstamo.",
            )
            return redirect("mis_prestamos")

        if Reserva.objects.filter(
            libro=libro,
            estado__in=["PENDIENTE", "DISPONIBLE"],
        ).exclude(usuario=usuario).exists():
            messages.error(
                request,
                "Otro lector tiene una reserva vigente de este título. "
                "No es posible renovarlo.",
            )
            return redirect("mis_prestamos")

        # RN-10: el plazo se cuenta desde el día de la renovación.
        prestamo.fecha_vencimiento = hoy + timedelta(days=dias)
        prestamo.num_renovaciones += 1
        prestamo.save(update_fields=[
            "fecha_vencimiento",
            "num_renovaciones",
        ])

    messages.success(
        request,
        f"Préstamo #{prestamo.pk} renovado. "
        f"Nuevo vencimiento: {prestamo.fecha_vencimiento:%d/%m/%Y}.",
    )
    return redirect("mis_prestamos")
@login_required
def registrar_incidencia_view(request, prestamo_id):
    from decimal import Decimal

    from django.db import transaction
    from django.shortcuts import get_object_or_404, redirect, render
    from django.utils import timezone

    from catalogo.models import Ejemplar
    from cuentas.models import Usuario
    from multas.models import Multa
    from prestamos.models import PoliticaPrestamo, Prestamo

    if request.user.tipo_usuario != "BIBLIOTECARIO":
        messages.error(request, "Acceso exclusivo para el bibliotecario.")
        return redirect("home")

    if request.method not in ("GET", "POST"):
        from django.http import HttpResponseNotAllowed

        return HttpResponseNotAllowed(["GET", "POST"])

    prestamo = get_object_or_404(
        Prestamo.objects.select_related(
            "usuario",
            "ejemplar__libro",
        ),
        pk=prestamo_id,
    )

    if prestamo.estado not in ("ACTIVO", "VENCIDO"):
        messages.error(request, "Este préstamo ya no admite incidencias.")
        return redirect("devoluciones_pendientes")

    context = {
        "prestamo": prestamo,
        "tipo_seleccionado": "",
        "descripcion": "",
    }

    if request.method == "GET":
        return render(
            request,
            "prestamos/registrar_incidencia.html",
            context,
        )

    tipo = request.POST.get("tipo", "").strip()
    descripcion = request.POST.get("descripcion", "").strip()

    context["tipo_seleccionado"] = tipo
    context["descripcion"] = descripcion

    if tipo not in ("DANIO", "PERDIDA"):
        messages.error(request, "Selecciona daño o pérdida.")
        return render(
            request,
            "prestamos/registrar_incidencia.html",
            context,
        )

    if not descripcion or len(descripcion) > 200:
        messages.error(
            request,
            "Escribe una descripción de entre 1 y 200 caracteres.",
        )
        return render(
            request,
            "prestamos/registrar_incidencia.html",
            context,
        )

    with transaction.atomic():
        # Mantener el mismo orden de bloqueo que las otras operaciones.
        usuario = Usuario.objects.select_for_update().get(
            pk=prestamo.usuario_id,
        )

        prestamo = Prestamo.objects.select_for_update().get(
            pk=prestamo.pk,
        )

        ejemplar = Ejemplar.objects.select_for_update().get(
            pk=prestamo.ejemplar_id,
        )

        # Bloquear el libro para leer su costo actual.
        from catalogo.models import Libro

        libro = Libro.objects.select_for_update().get(
            pk=ejemplar.libro_id,
        )

        # Volver a validar después de obtener los bloqueos.
        if prestamo.estado not in ("ACTIVO", "VENCIDO"):
            messages.error(
                request,
                "El préstamo ya fue procesado. Actualiza la página.",
            )
            return redirect("devoluciones_pendientes")

        if ejemplar.estado != "PRESTADO":
            messages.error(
                request,
                "El ejemplar no figura como prestado. Revisa su registro.",
            )
            return redirect("devoluciones_pendientes")

        if not prestamo.fecha_vencimiento:
            messages.error(
                request,
                "El préstamo no tiene una fecha de vencimiento registrada.",
            )
            return redirect("devoluciones_pendientes")

        costo = libro.costo_reposicion

        if costo is None or costo <= Decimal("0.00"):
            messages.error(
                request,
                "Registra un costo de reposición mayor que cero "
                "en el libro antes de continuar.",
            )
            return redirect("devoluciones_pendientes")

        if Multa.objects.filter(
            prestamo=prestamo,
            motivo__in=["DANIO", "PERDIDA"],
        ).exists():
            messages.error(
                request,
                "Este préstamo ya tiene una multa por daño o pérdida.",
            )
            return redirect("devoluciones_pendientes")

        ahora = timezone.now()
        hoy = timezone.localdate(ahora)

        dias_retraso = max(
            (hoy - prestamo.fecha_vencimiento).days,
            0,
        )

        politica = PoliticaPrestamo.objects.filter(
            tipo_usuario=usuario.tipo_usuario,
        ).first()

        tarifa = (
            politica.multa_por_dia
            if politica
            else Decimal("10.00")
        )
        limite = (
            politica.multa_maxima
            if politica
            else Decimal("300.00")
        )

        monto_retraso = min(
            Decimal(dias_retraso) * tarifa,
            limite,
        )

        if monto_retraso > 0:
            Multa.objects.get_or_create(
                prestamo=prestamo,
                motivo="RETRASO",
                defaults={
                    "usuario": usuario,
                    "dias_retraso": dias_retraso,
                    "monto": monto_retraso,
                    "estado": "PENDIENTE",
                },
            )

        multa = Multa.objects.create(
            prestamo=prestamo,
            usuario=usuario,
            motivo=tipo,
            dias_retraso=0,
            monto=costo,
            estado="PENDIENTE",
        )

        etiqueta = "Daño" if tipo == "DANIO" else "Pérdida"

        prestamo.observaciones = (
            f"{etiqueta} registrada por usuario "
            f"#{request.user.pk}: {descripcion}"
        )[:255]

        if tipo == "DANIO":
            prestamo.estado = "DEVUELTO"
            prestamo.fecha_devolucion = ahora
            prestamo.recibido_por = request.user
            ejemplar.estado = "EN_REPARACION"
        else:
            prestamo.estado = "PERDIDO"
            # No hubo devolución física del ejemplar.
            prestamo.fecha_devolucion = None
            prestamo.recibido_por = None
            ejemplar.estado = "PERDIDO"

        prestamo.save(
            update_fields=[
                "estado",
                "fecha_devolucion",
                "recibido_por",
                "observaciones",
            ],
        )

        ejemplar.save(update_fields=["estado"])

    messages.success(
        request,
        f"{etiqueta} registrada para el préstamo #{prestamo.pk}. "
        f"Multa #{multa.pk} por reposición: ${costo:.2f}.",
    )

    if monto_retraso > 0:
        messages.info(
            request,
            f"El préstamo también tiene una multa por retraso "
            f"de ${monto_retraso:.2f}.",
        )

    return redirect("devoluciones_pendientes")
@login_required
@require_POST
def cancelar_solicitud_view(request, prestamo_id):
    from django.contrib.auth import get_user_model
    from django.db import transaction
    from django.shortcuts import get_object_or_404, redirect
    from django.utils import timezone

    from catalogo.models import Ejemplar
    from prestamos.models import Prestamo

    if request.user.tipo_usuario not in ("ESTUDIANTE", "PROFESOR"):
        messages.error(request, "Esta opción es exclusiva para lectores.")
        return redirect("home")

    # Solo permite localizar solicitudes del usuario conectado.
    solicitud = get_object_or_404(
        Prestamo,
        pk=prestamo_id,
        usuario=request.user,
    )

    Usuario = get_user_model()

    with transaction.atomic():
        # Mismo orden de bloqueo que entrega y devolución.
        Usuario.objects.select_for_update().get(pk=request.user.pk)

        solicitud = get_object_or_404(
            Prestamo.objects.select_for_update(),
            pk=solicitud.pk,
            usuario=request.user,
        )

        ejemplar = Ejemplar.objects.select_for_update().get(
            pk=solicitud.ejemplar_id,
        )

        if solicitud.estado != "SOLICITADO":
            messages.error(
                request,
                "Solo puedes cancelar solicitudes pendientes de recoger.",
            )
            return redirect("mis_prestamos")

        if ejemplar.estado != "RESERVADO":
            messages.error(
                request,
                "El estado del ejemplar no coincide con la solicitud. "
                "Solicita al bibliotecario que revise el registro.",
            )
            return redirect("mis_prestamos")

        ahora = timezone.now()

        expirada = (
            solicitud.fecha_limite_recoger is not None
            and solicitud.fecha_limite_recoger <= ahora
        )

        solicitud.estado = "EXPIRADO" if expirada else "CANCELADO"
        solicitud.save(update_fields=["estado"])

        # Conserva la solicitud en el historial y atiende la cola de reservas.
        asignar_reserva_o_liberar(ejemplar, ahora)

    if expirada:
        messages.warning(
            request,
            f"La solicitud #{solicitud.pk} ya había superado "
            "su plazo de recogida y quedó expirada.",
        )
    else:
        messages.success(
            request,
            f"Solicitud #{solicitud.pk} cancelada correctamente.",
        )

    return redirect("mis_prestamos")