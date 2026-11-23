from django.urls import path
from . import views

urlpatterns = [
    path('mis-multas/', views.mis_multas_view, name='mis_multas'),
    path('pendientes/', views.multas_pendientes_view, name='multas_pendientes',),
    path('<int:multa_id>/pagar/', views.registrar_pago_view, name='registrar_pago',),
]