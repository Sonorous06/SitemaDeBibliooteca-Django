from django.urls import path 
from . import views 

urlpatterns = [
    # Gestión de Usuarios (Exclusivo Bibliotecario - CU-20 y CU-22)
    path('usuarios/', views.lista_usuarios_view, name='lista_usuarios'), 
    
    path('usuarios/<int:usuario_id>/bloquear/', views.alternar_bloqueo_usuario_view, name='alternar_bloqueo_usuario'),
    
    #recuperacion de contraseña personalizada | envio correo cu 03
    path('recuperar-password/', views.recuperar_password_custom_view, name='password_reset'),
]
