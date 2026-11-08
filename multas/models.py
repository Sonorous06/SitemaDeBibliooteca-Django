from django.db import models 
from django.conf import settings 
from django.utils import timezone 
from prestamos.models import Prestamo 

class Multa(models.Model): 
    MOTIVOS = [
        ('RETRASO', 'Entrega tardía'), 
        ('DANIO', 'Daño del ejemplar'), 
        ('PERDIDA', 'Pérdida del ejemplar'),
        ]
    ESTADOS = [
        ('PENDIENTE', 'Pendiente'), 
        ('PAGADA', 'Pagada'), 
        ('CONDONADA', 'Condonada'),
        ] 
    
    prestamo = models.ForeignKey(Prestamo, on_delete=models.PROTECT, related_name='multas')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='multas') 
    motivo = models.CharField(max_length=10, choices=MOTIVOS) 
    dias_retraso = models.PositiveSmallIntegerField(default=0) 
    monto = models.DecimalField(max_digits=10, decimal_places=2) 
    estado = models.CharField(max_length=10, choices=ESTADOS, default='PENDIENTE')
    fecha_generacion = models.DateTimeField(default=timezone.now)
    
    justificacion_condonacion = models.CharField(max_length=255, blank=True, null=True) 
    condonada_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='multas_condonadas') 
    
    class Meta: 
        db_table = 'multa' 
        
        def __str__(self): 
            return f"Multa #{self.id} (${self.monto}) - {self.usuario.username} ({self.estado})"
         
class Pago(models.Model): 
        METODOS = [
            ('EFECTIVO', 'Efectivo'), 
            ('TARJETA', 'Tarjeta'),
            ('TRANSFERENCIA', 'Transferencia'),
        ] 
        
        multa = models.ForeignKey(Multa, on_delete=models.PROTECT, related_name='pagos')
        monto = models.DecimalField(max_digits=10, decimal_places=2) 
        metodo = models.CharField(max_length=15, choices=METODOS)
        folio_recibo = models.CharField(max_length=30, unique=True)
        fecha_pago = models.DateTimeField(default=timezone.now)
        registrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='pagos_registrados') 
        
        class Meta: 
            db_table = 'pago' 
            
        def __str__(self): 
            return f"Pago {self.folio_recibo} - ${self.monto}"