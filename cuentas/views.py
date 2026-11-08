from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Q

from .models import Usuario
from prestamos.models import Prestamo
from catalogo.models import Libro

# Vista principal.
@login_required
def home_view(request):
    """Muestra la página principal alimentando las métricas en tiempo real."""
    hoy = timezone.localdate()
    en_una_semana = hoy + timedelta(days=7)
    
    #consultas ORM para las tarjetas 
    #solicitudes de prestamo pendientes
    solicitudes_pendientes = Prestamo.objects.filter(estado='SOLICITADO').count()
    
    #libros prestados que se deben devolver hoy
    devoluciones_hoy = Prestamo.objects.filter(fecha_vencimiento=hoy, estado='ACTIVO').count()
    
    #prestamos cuya fecha ya paso
    prestamos_vencidos = Prestamo.objects.filter(fecha_vencimiento__lt=hoy, estado='ACTIVO').count()
    
    #prestmaos que venceran en 7 dias
    prestamos_vencen_semana = Prestamo.objects.filter(
        fecha_vencimiento__range = [hoy, en_una_semana],
        estado='ACTIVO'
    ).select_related('ejemplar__libro','usuario')[:5]
    
    libros_poco_stock = Libro.objects.annotate(
        stock_disponible=Count('ejemplares', filter=Q(ejemplares__estado='DISPONIBLE'))
    ).filter(stock_disponible__lte=2)[:5]
    
    context = {
        'solicitudes_pendientes' : solicitudes_pendientes,
        'devoluciones_hoy' : devoluciones_hoy,
        'prestamos_vencidos' : prestamos_vencidos,
        'prestamos_vencen_semana' : prestamos_vencen_semana,
        'libros_poco_stock' : libros_poco_stock,
    }
    
    return render(request, 'home.html', context)

#administracion de usuarios y bloqueos (CU-20 Y CU-22)
@login_required
def lista_usuarios_view(request):
    """ Permite al bibliotecario consultar la lista de usuarios del sistema (CU-20). """
    if request.user.tipo_usuario != 'BIBLIOTECARIO':
        messages.error(request, "Acceso no autorizado")
        return redirect('catalogo')
    
    usuarios = Usuario.objects.all().order_by('username')
    return render(request,'cuentas/lista_usuarios.html' , {'usuarios': usuarios})

@login_required
def alternar_bloqueo_usuario_view(request, usuario_id):
    """ Permite al bibliotecario bloquear o desbloquear la cuenta de un usuario"""
    if request.user.tipo_usuario != 'BIBLIOTECARIO':
        messages.error(request, "Acceso no autorizado")
        return redirect('catalogo')
    
    usuario = get_object_or_404(Usuario, pk=usuario_id)
    
    #alternar estado de bloqueo
    usuario.bloqueado = not usuario.bloqueado
    if usuario.bloqueado:
        usuario.motivo_bloqueo = "Bloqueo por el bibliotecario"
    else:
        usuario.motivo_bloqueo = None
        
    usuario.save()
    
    estado_txt = "BLOQUEADO" if usuario.bloqueado else "DESBLOQUEADO"
    messages.success(request,f"La cuenta de {usuario.username} ha sido {estado_txt} correctamente.")
    return redirect('lista_usuarios_view')
        

#MODULO 2 --PRESTAMOS
@login_required

def prestamos_view(request):
    return HttpResponse(""" 
        <h1>Mis presstamos</h1> 
        <br> 
        <a href="/">Volver al Inicio</a> 
    """)

#MODULO 3 --HISTORIAL Y PENALIZACION
@login_required
def historial_view(request):
    return HttpResponse(""" 
        <h1>Historial y Penalizaciones</h1> 
        <br> 
        <a href="/">Volver al Inicio</a> 
    """)