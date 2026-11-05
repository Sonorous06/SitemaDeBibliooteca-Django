from django.urls import path
from django.contrib.auth import views as auth_views 
from .views import home_view, prestamos_view, historial_view

#vistas importadas
from catalogo.views import ( 
    catalogo_view, 
    sugerir_adquisicion_view, 
    lista_sugerencias_view, 
    cambiar_estado_sugerencia
)

urlpatterns = [
       # Página de bienvenida 
        path('', home_view, name='home'), 
           
        #Autenticacion
        path('login/', auth_views.LoginView.as_view(template_name='cuentas/login.html'), name='login'),         
        path('logout/', auth_views.LogoutView.as_view(), name='logout'),
            
        #rutas catalogo
        path('catalogo/', catalogo_view, name='catalogo'),         
        path('catalogo/sugerir/', sugerir_adquisicion_view, name='sugerir_adquisicion'), 
        path('catalogo/sugerencias/', lista_sugerencias_view, name='lista_sugerencias'), 
        path('catalogo/sugerencias/<int:sugerencia_id>/<str:nuevo_estado>/', cambiar_estado_sugerencia, name='cambiar_estado_sugerencia'),
            
        #rutas temporales
        path('prestamos/', prestamos_view, name='prestamos'), 
        path('historial/', historial_view, name='historial')
]