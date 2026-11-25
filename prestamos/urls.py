from django.urls import path
from . import views

urlpatterns = [
    path('solicitar/<int:libro_id>/', views.solicitar_prestamo_view, name='solicitar_prestamo'),
    
    path('entregar/<int:prestamo_id>',views.entregar_prestamo_view, name='entregar_prestamo'),
    
    path('devolver/<int:prestamo_id>', views.devolver_prestamo_view, name='devolver_prestamo'),

    path('mis-prestamos/', views.mis_prestamos_view, name='mis_prestamos'),

    path('solicitudes/',views.solicitudes_pendientes_view, name='solicitudes_pendientes',),
    
    path('devoluciones/',views.devoluciones_pendientes_view, name='devoluciones_pendientes',),

    path("reservar/<int:libro_id>/", views.reservar_libro_view, name="reservar_libro",),

    path("mis-reservas/", views.mis_reservas_view, name="mis_reservas",),

    path("reservas/<int:reserva_id>/cancelar/",views.cancelar_reserva_view,name="cancelar_reserva",),

    path("reservas/por-entregar/",views.reservas_para_entregar_view,name="reservas_para_entregar",),

    path("reservas/<int:reserva_id>/recoger/",views.recoger_reserva_view,name="recoger_reserva",),

    path("renovar/<int:prestamo_id>/",views.renovar_prestamo_view,name="renovar_prestamo",),
]