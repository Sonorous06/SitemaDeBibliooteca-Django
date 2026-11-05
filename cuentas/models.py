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
    
#catalogo de carreras(estudiantes)
class Carrera(models.Model):
    clave = models.CharField(max_length=10, unique=True, verbose_name="Clave de Carrera")
    nombre = models.CharField(max_length=120, verbose_name="Nombre de la carrera")
    
    class Meta:
        db_table = 'carrera'
        verbose_name = 'Carrera'
        verbose_name_plural = 'Carreras'
    
    def __str__(self):
        return f"{self.clave} - {self.nombre}"

#perfil de estudiante (relac 1 a 1 con usuario)
class Estudiante(models.Model):
     usuario = models.OneToOneField(
         Usuario,
         on_delete=models.CASCADE,
         primary_key=True,
         related_name='estudiante'
     )
     matricula = models.CharField(max_length=20, unique=True, verbose_name='Matricula')
     carrera = models.ForeignKey(Carrera, on_delete=models.PROTECT, verbose_name='Carrera')
     semestre = models.PositiveSmallIntegerField(verbose_name='Semestre')
     
     class Meta:
             db_table = 'estudiante'
             verbose_name = 'Estudiante'
             verbose_name_plural = 'Estudiantes'

    
#catalogo de departamentos
class Departamento(models.Model):
    nombre = models.CharField(max_length=120, unique=True, verbose_name="Nombre del Departamento")
    
    class Meta:
        db_table = 'departamento'
        verbose_name = 'Departamento'
        verbose_name_plural = 'Departamentos'
        
    def __str__(self): 
        return self.nombre

#perfilde profesor (relacion 1 a 1 con usurio)
class Profesor(models.Model):
    usuario = models.OneToOneField(
        Usuario,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='profesor'        
    )
    num_empleado = models.CharField(max_length=20, unique=True, verbose_name="Número de Empleado")
    departamento = models.ForeignKey(Departamento, on_delete=models.PROTECT, verbose_name="Departamento")
    
    class Meta:
        db_table = 'profesor'
        verbose_name = 'Profesor'
        verbose_name_plural = 'Profesores'
        
    def __str__(self):
        return f"{self.usuario.get_full_name() or self.usuario.username} ({self.num_empleado})"