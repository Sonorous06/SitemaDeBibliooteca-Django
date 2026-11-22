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
def devolver_prestamo_view(request, prestamo_id):
    """Registra la devolución del libro. Si hay retraso, genera multa automáticamente."""
    if request.user.tipo_usuario != 'BIBLIOTECARIO':
        messages.error(request, "Acceso no autorizado")
        return redirect('home')
    
    prestamo = get_object_or_404(Prestamo, pk=prestamo_id, estado__in=['ACTIVO','VENCIDO'])  
    hoy = timezone.localdate()
    
    with transaction.atomic():
        prestamo.estado = 'DEVUELTO'
        prestamo.fecha_devolucion = timezone.now()
        prestamo.recibido_por = request.user
        prestamo.save()
    
        # calculo de multa por morosidad rn-04 / rn-07
        if hoy > prestamo.fecha_vencimiento:
            dias_retraso = (hoy - prestamo.fecha_vencimiento).days
            politica = PoliticaPrestamo.objects.filter(tipo_usuario=prestamo.usuario.tipo_usuario).first()
            tarifa = politica.multa_por_dia if politica else 10.00
            tope = politica.multa_maxima if politica else 300.00
            
            monto_calculado = min(dias_retraso * float())
            
            Multa.objects.create(
                usuario=prestamo.usuario, 
                prestamo=prestamo, 
                monto=monto_calculado, 
                dias_retraso=dias_retraso, 
                motivo=f"Retraso de {dias_retraso} días en la devolución del libro.", estado='PENDIENTE'
            )
            
            messages.warning(
                request,
                f"Préstamo devuelto con {dias_retraso} días de morosidad. Se generó una multa por ${monto_calculado:.2f} MXN."
            )
        else :
            messages.success(request, f"Préstamo # {prestamo.id} devuelto a tiempo sin penalizaciones.")
            
            
        #reasignacion por cola de reservas FIFO rn-12
        reserva_siguiente = Reserva.objects.filter(
            libro=prestamo.ejemplar.libro, estado='PENDIENTE'
        ).order_by('fecha_solicitud').first()
        
        ejemplar = prestamo.ejemplar 
        
        if reserva_siguiente:
            ejemplar.estado = 'RESERVADO'
            reserva_siguiente.estado = 'ASIGNADO' 
            reserva_siguiente.fecha_asignacion = timezone.now()
            reserva_siguiente.save() 
        else: 
            ejemplar.estado = 'DISPONIBLE' 
        ejemplar.save()
        
    return redirect('home')

#historial "mis prestamos" CU-07
@login_required
def mis_prestamos_view(request):
    """Muestra al usuario la lista de sus préstamos activos y pasados."""
    prestamos = Prestamo.objects.filter(usuario=request.user).select_related('ejemplar__libro').order_by('-fecha_solicitud')
    return render(request, 'prestamos/mis_prestamos.html', {'prestamos': prestamos})
@login_required
def solicitudes_pendientes_view(request):
    """Muestra las solicitudes que el bibliotecario puede entregar."""
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