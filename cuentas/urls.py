from django.contrib.auth import views as auth_views
from django.urls import path 
from . import views 
from . import views_lectores
from . import views_importacion

urlpatterns = [
    # Gestión de Usuarios (Exclusivo Bibliotecario - CU-20 y CU-22)
    path('usuarios/', views.lista_usuarios_view, name='lista_usuarios'), 
    
    path('usuarios/<int:usuario_id>/bloquear/', views.alternar_bloqueo_usuario_view, name='alternar_bloqueo_usuario'),
    
    #recuperacion de contraseña personalizada | envio correo cu 03
    path('recuperar-password/',auth_views.PasswordResetView.as_view(template_name='registration/password_reset_form.html',),name='password_reset',),
    path(
        "usuarios/crear/",
        views_lectores.crear_lector_view,
        name="crear_lector",
    ),
    path(
        "usuarios/<int:usuario_id>/editar/",
        views_lectores.editar_lector_view,
        name="editar_lector",
    ),
    path(
        "usuarios/importar/",
        views_importacion.importar_lectores_view,
        name="importar_lectores",
    ),
]
