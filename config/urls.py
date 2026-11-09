
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # Panel de administración Django
    path("admin/", admin.site.urls),
    
    # Módulo de cuentas y autenticación
    path('', include('cuentas.urls')),
    
    # Módulo del catálogo
    path('catalogo/', include('catalogo.urls')),
    
    # Módulo de préstamos
    path('prestamos/', include('prestamos.urls')),
]
