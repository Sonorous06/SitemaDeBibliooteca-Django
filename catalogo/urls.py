from django.urls import path 
from . import views 

urlpatterns = [
    # Vista principal del catálogo 
    path('', views.catalogo_view, name='catalogo'), 
    
    # Vista del detalle de un libro (si ya la tienen definida)
    path('<int:libro_id>', views.catalogo_view, name='detalle_libro')
]