from django.urls import path
from . import views

urlpatterns = [
    path("",views.mis_notificaciones_view,name="mis_notificaciones",),
    path("<int:notificacion_id>/leer/",views.marcar_leida_view,name="marcar_notificacion_leida",),
]