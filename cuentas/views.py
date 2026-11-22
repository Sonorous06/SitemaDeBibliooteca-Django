from django.db import transaction
from django.views.decorators.http import require_POST
from datetime import timedelta 
from django.conf import settings 
from django.contrib import messages 
from django.contrib.auth import get_user_model 
from django.contrib.auth.decorators import login_required 
from django.contrib.auth.tokens import default_token_generator 
from django.core.mail import send_mail 
from django.db.models import Count, Q 
from django.shortcuts import get_object_or_404, redirect, render 
from django.utils import timezone 
from django.utils.encoding import force_bytes 
from django.utils.http import urlsafe_base64_encode

from .models import Usuario
from prestamos.models import Prestamo
from catalogo.models import Libro
from .forms import RecuperarPasswordCustomForm

User = get_user_model()

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
@require_POST
def alternar_bloqueo_usuario_view(request, usuario_id):
    """Permite al bibliotecario bloquear o desbloquear una cuenta."""
    if request.user.tipo_usuario != 'BIBLIOTECARIO':
        messages.error(request, 'Acceso no autorizado.')
        return redirect('catalogo')

    if usuario_id == request.user.pk:
        messages.error(request, 'No puedes bloquear tu propia cuenta.')
        return redirect('lista_usuarios')

    with transaction.atomic():
        usuario = get_object_or_404(
            Usuario.objects.select_for_update(),
            pk=usuario_id
        )

        if usuario.bloqueado:
            usuario.bloqueado = False
            usuario.motivo_bloqueo = None
            mensaje = f'Se desbloqueó la cuenta de {usuario.username}.'
        else:
            motivo = request.POST.get('motivo_bloqueo', '').strip()

            if not motivo:
                messages.error(request, 'Escribe el motivo del bloqueo.')
                return redirect('lista_usuarios')

            if len(motivo) > 255:
                messages.error(
                    request,
                    'El motivo debe tener como máximo 255 caracteres.'
                )
                return redirect('lista_usuarios')

            usuario.bloqueado = True
            usuario.motivo_bloqueo = motivo
            mensaje = f'Se bloqueó la cuenta de {usuario.username}.'

        usuario.save(update_fields=['bloqueado', 'motivo_bloqueo'])

    messages.success(request, mensaje)
    return redirect('lista_usuarios')
        
#recuperacion de contraseña personalizada
def recuperar_password_custom_view(request):
    """Permite ingresar un usuario/matrícula y enviar el correo de recuperación a la dirección . """
    
    if request.method == 'POST':
        form = RecuperarPasswordCustomForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            correo_destino = form.cleaned_data['correo_destino']
            
            user = User.objects.get(username__iexact=username, is_active=True)
            
            #generacion del uid y token 
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            
            domain = request.get_host()
            protocol = 'https' if request.is_secure() else 'http'
            reset_url = f'{protocol}://{domain}/cuentas/reset/{uid}/{token}/'
            
            subject = 'Restablecimiento de contraseña - Biblioteca'
            message = (
                f'Hola {user.get_full_name() or user.username},\n\n' 'Hemos recibido una solicitud para restablecer tu contraseña.\n\n' 'Haz clic en el siguiente enlace para ingresar tu nueva' f' contraseña:\n{reset_url}\n\n' 'Atentamente,\nEquipo de Biblioteca Escolar'
            )
            
            #Envio directo al correo elegido
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [correo_destino],
                fail_silently=False
            )
            return redirect('password_reset_done')
    else:
        form = RecuperarPasswordCustomForm()

    return render(
        request,
        'registration/password_reset_form.html',
        {'form': form}
    )
