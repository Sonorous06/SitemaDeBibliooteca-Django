from django.db import models

#esta es la clase base de usuarios, ya incluye username , emial , password etc
from django.contrib.auth.models import AbstractUser

#se hereda esta clase para la funcionalidad de los login
class Usuario(AbstractUser):
    
    email = models.EmailField(unique=True, null=True, blank=True, verbose_name="Correo Electrónico")
    
    #restringe roles a los permitidos
    TIPO_USUARIO_CHOICES = (
        ('ESTUDIANTE','Estudiante'),
        ('PROFESOR','Profesor'),
        ('BIBLIOTECARIO','Bibliotecario'),
    )
        
    tipo_usuario = models.CharField(
        max_length=15,
        choices=TIPO_USUARIO_CHOICES,
        default='ESTUDIANTE',
        verbose_name="Tipo de Usuario"
    )
    
    telefono = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="Telefono"
    )
    
    #permite al bibliotecario suspender cuentas
    bloqueado = models.BooleanField(
        default=False,
        verbose_name="Bloqueado"
    )
    
    #suspender cuentas
    motivo_bloqueo = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Motivo de bloqueo"
    )
    
    class Meta:
        db_table = 'usuario'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        
    def save(self, *args, **kwargs):
        if not self.email:
            self.email = f"{self.username}@anahuac.com"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.username} ({self.get_tipo_usuario_display()})"
    