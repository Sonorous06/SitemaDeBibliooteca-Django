from django.db import models
from django.conf import settings
from django.utils import timezone

class Notificacion(models.Model):
    TIPOS = [
        ('VENCE_PRONTO','Vencimiento Proximo'),
        ('VENCIDO', 'Prestamo Vencido'),
        ('RESERVA_DISPONIBLE', 'Reserva Disponible'),
        ('MULTA', 'Multa Generada'),
        ('GENERAL', 'Aviso General'),
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notificaciones',
    )

    tipo = models.CharField(max_length=20, choices=TIPOS, default='GENERAL')
    mensaje = models.CharField(max_length=500)
    leida = models.BooleanField(default=False)
    fecha = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'notificacion'
        ordering = ['-fecha']

        def __str__(self):
            return f'Notificacion para {self.usuario.username} - {self.get_tipo_display()}'


