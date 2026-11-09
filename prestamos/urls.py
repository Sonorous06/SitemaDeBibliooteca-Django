from django.urls import path
from . import views

urlpatterns = [
    path('solicitar/<int:libro_id>/', views.solicitar_prestamo_view, name='solicitar_prestamo'),
    
    path('entregar/<int:prestamo_id>',views.entregar_prestamo_view, name='entregar_prestamo'),
    
    path('devolver/<int:prestamo_id>', views.devolver_prestamo_view, name='devolver_prestamo'),
    
    path('mis-prestamos/', views.mis_prestamos_view, name='mis_prestamos')
]