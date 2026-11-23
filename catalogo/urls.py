from django.urls import path 
from . import views 

urlpatterns = [
    # Vista principal del catálogo 
    path('', views.catalogo_view, name='catalogo'), 
    
    # Vista del detalle de un libro (si ya la tienen definida)
    path('<int:libro_id>', views.catalogo_view, name='detalle_libro'),
    
    #rutas de sugerecias
    #formulario para que el profe siguiera un libro
    path('sugerir/', views.sugerir_adquisicion_view, name='sugerir_adquisicion'),
    
    #lista de sugerecnias para que el bibiliotecario las revise
    path('sugerencias/', views.lista_sugerencias_view, name='lista_sugerencias'),
    
    #accion para aprobar o rechazar
    path('sugerencias/<int:sugerencia_id>/<str:nuevo_estado>/', views.cambiar_estado_sugerencia, name='cambiar_estado_sugerencia'),
]