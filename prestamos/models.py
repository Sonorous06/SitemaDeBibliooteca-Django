from django.db import models
from django.conf import settings
from django.utils import timezone
from catalogo.models import Ejemplar, Libro

# politica de prestamos por tipo de usuario (RN-01 a RN-06)
class PoliticaPrestamo(models.Model):
    TIPO_USUARIO_CHOICES = [
        ('ESTUDIANTE','Estudiante'),
        ('PROFESOR','Profesor'),
    ]

    tipo_usuario = models.CharField(max_length=15, unique=True,choices=TIPO_USUARIO_CHOICES)
    dias_prestamos = models.PositiveSmallIntegerField(help_text="Dias naturales de prestamo")
    max_libros = models.PositiveSmallIntegerField(help_text="Maximos de libros simultaneos")
    max_renovaciones = models.PositiveSmallIntegerField(help_text="Renovaciones permitidas")
    multa_por_dia = models.DecimalField(max_digits=8, decimal_places=2, help_text="Costo por dia de mora")
    multa_maxima = models.DecimalField(max_digits=8, decimal_places=2, help_text="Tope maximo de multa por retraso")
    horas_para_recoger = models.PositiveSmallIntegerField(default=48, help_text="Horas para recoger solicitud/reserva")
    actualizado_en = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'polica_prestamo'
    
    def __str__(self):
        return f"Política {self.tipo_usuario}"

#prestamos (ciclo de vida completo del prestamo)
class Prestamo(models.Model):
    ESTADOS = [
           ('SOLICITADO','Solicitado'),
           ('ACTIVO', 'Activo'), 
           ('VENCIDO', 'Vencido'), 
           ('DEVUELTO', 'Devuelto'), 
           ('CANCELADO', 'Cancelado'), 
           ('EXPIRADO', 'Expirado'), 
           ('PERDIDO', 'Perdido'),
    ]
    
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='prestamos') 
    ejemplar = models.ForeignKey(Ejemplar, on_delete=models.PROTECT, related_name='prestamos') 
    estado = models.CharField(max_length=12, choices=ESTADOS, default='SOLICITADO')
    
    fecha_solicitud = models.DateTimeField(default=timezone.now)
    fecha_limite_recoger = models.DateTimeField(blank=True, null=True) 
    fecha_prestamo = models.DateTimeField(blank=True, null=True) 
    fecha_vencimiento = models.DateField(blank=True, null=True) 
    fecha_devolucion = models.DateTimeField(blank=True, null=True)
    
    num_renovaciones = models.PositiveSmallIntegerField(default=0) 
    entregado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='prestamos_entregados') 
    recibido_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='prestamos_recibidos') 
    observaciones = models.CharField(max_length=255, blank=True, null=True)
    
    class Meta:
        db_table = 'prestamo'
        
    def __str__(self):
        return f"Préstamo #{self.id} - {self.usuario.username} ({self.ejemplar.codigo_inventario})"
    
    def dias_retraso(self, fecha_referencia=None):
        """Calcula los días transcurridos después de la fecha de vencimiento (RN-07)."""
        ref = fecha_referencia or timezone.localdate()
        if not self.fecha_vencimiento or ref <= self.fecha_vencimiento:
            return 0
        return (ref - self.fecha_vencimiento).days
    
    def calcular_multa_monto(self, politica):
        """Aplica la fórmula: min(días × multa_por_día, multa_máxima) (RN-07)."""
        dias = self.dias_retraso()
        if dias <= 0:
            return 0
        monto_calculado = dias * politica.multa_por_dia
        return min(monto_calculado, politica.multa_maxima)
    
#reservas (cola fifo libros sin stock)
class Reserva(models.Model):
    ESTADOS = [
        ('PENDIENTE', 'Pendiente'), 
        ('DISPONIBLE', 'Disponible para recoger'), 
        ('ATENDIDA', 'Atendida'), 
        ('CANCELADA', 'Cancelada'), 
        ('EXPIRADA', 'Expirada'),
    ]
    
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='reservas') 
    libro = models.ForeignKey(Libro, on_delete=models.PROTECT, related_name='reservas')
    ejemplar_asignado = models.ForeignKey(Ejemplar, on_delete=models.SET_NULL, null=True, blank=True, related_name='reservas_asignadas')
    estado = models.CharField(max_length=12, choices=ESTADOS, default='PENDIENTE')
    fecha_reserva = models.DateTimeField(default=timezone.now) 
    fecha_expiracion = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'reserva'
        ordering = ['fecha_reserva'] #garatinza la cola RN-12
        
    def __str__(self):
        return f"Reserva de {self.libro.titulo} por {self.usuario.username}"