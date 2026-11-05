
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    
    #panel de administracion django
    path("admin/", admin.site.urls),
    
    #modulo de cuentas y auth
    path('', include('cuentas.urls'))

    
]
