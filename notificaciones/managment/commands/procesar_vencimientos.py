from django.core.management.base import BaseCommand 
from django.utils import timezone 
from datetime import timedelta 
from prestamos.models import Prestamo, Reserva, PoliticaPrestamo 
from multas.models import Multa 
from notificaciones.models import Notificacion

class Command(BaseCommand):
    help = "CU-34 a CU-36: Procesa vencimientos de préstamos, calcula multas por mora y expira reservas no recogidas."

    def handle(self, *args, **option):
        hoy = timezone.localdate()
        ahora = timezone.now()

        #1 CU-34|RN-07: Marcar préstamos vencidos y generar/actualizar multas
        prestamos_vencidos = Prestamo.objects.filter(
            estado__in = ['ACTIVO','VENCIDO'],
            fecha_vencimiento__lt = hoy
        )

        multas_procesadas = 0
        for p in prestamos_vencidos:
            if p.estado == 'ACTIVO':
                p.estado = 'VENCIDO'
                p.save()

            politica = PoliticaPrestamo.objects.filter(tipo_usuario=p.usuario.tipo_usuario,).first()
            tarifa = politica.multa_por_dia if politica else 10.00
            tope = politica.multa_maxima if politica else 100.00

            dias_retraso = (hoy - p.fecha_vencimiento).days
            monto_calculado = min(dias_retraso * float(tarifa), float(tope))

            multa, creada = Multa.objects.get_or_create(
                prestamo=p,
                usuario=p.usuario,
                motivo='RETRASO',
                defaults={
                    'monto': monto_calculado, 
                    'dias_retraso': dias_retraso,
                    'estado' : 'PENDIENTE',
                }
            )

            if not creada and multa.estado == 'PENDIENTE':
                multa.monto = monto_calculado
                multa.dias_retraso = dias_retraso
                multa.save()

            # CU-36: Notificar al usuario sobre el vencimiento 
            Notificacion.objects.get_or_create(
                usuario=p.usuario, 
                tipo='VENCIDO', 
                mensaje=f"Tu préstamo de '{p.ejemplar.libro.titulo}' está vencido ({dias_retraso} días de morosidad). Multa acumulada: ${monto_calculado:.2f} MXN.",
                leida=False
                ) 
            multas_procesadas += 1

        #2 CU-35|RN-06: Expirar solicitudes/reservas no recogidas en 48 hrs y reasignar (FIFO)
        reservas_por_expirar = Reserva.objects.filter(
            estado='PENDIENTE',
            fecha_expiracion__lt=ahora
        )

        expiradas_count = 0
        for r in reservas_por_expirar:
            r.estado = 'EXPIRADA'
            r.save()
            expiradas_count += 1

            ejemplar = r.ejemplar_asignado

            #RN12 : Asignar al siguiente en la cola fifo
            siguiente = Reserva.objects.filter(
                libro=r.libro,
                estado='PENDIENTE',
            ).order_by('fecha_solicitud').first()

            if siguiente and ejemplar:
                siguiente.estado = 'DISPONIBLE' 
                siguiente.ejemplar_asignado = ejemplar 
                siguiente.fecha_expiracion = ahora + timedelta(hours=48) 
                siguiente.save() 

                Notificacion.objects.get_or_create(
                    usuario=siguiente.usuario,
                    tipo='RESERVA_DISPONIBLE',
                    mensaje=f"¡Tu reserva para '{r.libro.titulo}' ya está disponible! Tienes 48 hrs para recoger el ejemplar ({ejemplar.codigo_inventario})."
                )
            elif ejemplar:
                ejemplar.estado = 'DISPONIBLE'
                ejemplar.save()

        self.stdout.write(self.style.SUCCESS( 
            f"Proceso completado: {multas_procesadas} préstamos/multas actualizados y {expiradas_count} reservas expiradas." 
            ))