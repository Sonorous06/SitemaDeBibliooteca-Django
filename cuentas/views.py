from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from .models import Usuario

# Vista principal.
@login_required
def home_view(request):
    """Muestra la pagina principal solo si el usuario ha iniciado sesion"""
    return render(request, 'home.html')

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
    if request.user.tipo_usurio != 'BIBLIOTECARIO':
        messages.error(request, "Acceso no autorizado")
        return redirect('catalogo')
    
    usuario = get_object_or_404(Usuario, id=usuario_id)
    usuario.bloqueado = not usuario.bloqueado
    
    if usuario.bloqueado:
        usuario.motivo_bloqueo = "Bloqueo por el bibliotecario"
    else:
        usuario.motivo_bloqueo = None
        
    usuario.save()
    
    estado_str = "BLOQUEADO" if usuario.bloqueado else "DESBLOQUEADO"
    messages.success(request, f"El usuario {usuario.username} ha sido {estado_str} correctamente.")
    return redirect('lista_usuarios')
        

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