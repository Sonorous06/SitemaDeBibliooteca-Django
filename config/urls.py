
from django.contrib import admin
from django.urls import path, include 
from cuentas.views import home_view 
from django.contrib.auth import views as auth_views


urlpatterns = [
    path('admin/' , admin.site.urls),
    path('', home_view, name='home'),
    
    #rutas de app cuentas
    path('cuentas/', include('cuentas.urls')),

    #rutas nativas de login/logout
    path('login/', auth_views.LoginView.as_view(template_name='cuentas/login.html'), name='login'), 
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),path('cuentas/', include('django.contrib.auth.urls')),
        
    #otras apps (catalogo, prestamos, multas)
    path('catalogo/', include('catalogo.urls')),
    path('prestamos/', include('prestamos.urls'))
]