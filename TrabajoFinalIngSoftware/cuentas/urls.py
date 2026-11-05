from django.urls import path 
from django.contrib.auth import views as auth_views 
from .views import home_view, prestamos_view, historial_view
from catalogo.views import catalogo_view

urlpatterns = [
    #pag de bienvenida
   path('', home_view, name='home'),
   
   #auth de los usuariuos
   path('login/', auth_views.LoginView.as_view(template_name='cuentas/login.html'), name='login'),
   path('logout/', auth_views.LogoutView.as_view(), name='logout'),
   
   #rutas temporales
   path('catalogo/', catalogo_view, name='catalogo'), 
   path('prestamos/', prestamos_view, name='prestamos'), 
   path('historial/', historial_view, name='historial'),
]