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
def solicitar_prestamos_view(request, libro_id):
    """Permite al usuario solicitar un libro disponible desde el catálogo."""
    libro = get_object_or_404(Libro, pk=libro_id)
    
    #valida elegibilidad del usuario (sin multas pendientes ni vencidas)
    puede_pedir, mensaje_error = request.user.puede_solicitar_prestamo()
    if not puede_pedir:
        messages.error(request, mensaje_error)
        return redirect('catalogo')
    
    #busca ejemplar disponible en estante
    ejemplar = Ejemplar.objects.filter(libro=libro, estado='DISPONIBLE').first()
    if not ejemplar:
        messages.warning(request, f"No hay ejemplares disponibles de '{libro.titulo}'.")
        return redirect('catalogo')
    
    politica = PoliticaPrestamo.object.filter(tipo_usuario=request.user.tipo_usuario).first()
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
def entregar_prestamo_view(request, prestamo_id):
    """El bibliotecario aprueba y entrega el ejemplar físicamente en mostrador."""
    if request.user.tipo_usuario != 'BIBLIOTECARIO':
        messages.error(request, "Acceso no autorizado")
        return redirect('home')
    
    prestamo = get_object_or_404(Prestamo, pk=prestamo_id, estado='SOLICITADO')
    politica = PoliticaPrestamo.objects.filter(tipo_usuario=prestamo.usuario.tipo_usuario).first()
    dias = politica.dias_prestamos if politica else 7
    hoy = timezone.localdate()
    
    #TODO: INVESTIGAR PARA QUE SIRVE ESTO
    with transaction.atomic():
        prestamo.estado = 'ACTIVO'
        prestamo.fecha_prestamo = timezone.now()
        prestamo.fecha_vencimiento = hoy + timedelta(days=dias)
        prestamo.entregado_por = request.user
        prestamo.save()
        
    messages.success(
        request,
        f"Préstamo #{prestamo.id} activado. Fecha de vencimiento: {prestamo.fecha_vencimiento.strftime('%d/%m/%Y')}."
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