from django.urls import path
from . import views

urlpatterns = [
    path('mis-multas/', views.mis_multas_view, name='mis_multas'),
]