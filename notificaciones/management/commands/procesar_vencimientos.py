from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from catalogo.models import Ejemplar
from notificaciones.models import Notificacion
from prestamos.models import PoliticaPrestamo, Prestamo, Reserva


Usuario = get_user_model()


class Command(BaseCommand):
    help = (
        "Marca préstamos vencidos, expira solicitudes y reservas "
        "y genera recordatorios."
    )

    def avisar(self, usuario_id, tipo, mensaje):
        # Repetir el comando no duplica el mismo aviso.
        Notificacion.objects.get_or_create(
            usuario_id=usuario_id,
            tipo=tipo,
            mensaje=mensaje,
        )

    def reasignar_ejemplar(self, ejemplar, ahora):
        # Este método se ejecuta dentro de una transacción,
        # con el ejemplar bloqueado.
        if ejemplar.estado != "RESERVADO":
            return

        # Conservamos cualquier otra asignación vigente.
        if Prestamo.objects.filter(
            ejemplar=ejemplar,
            estado__in=["SOLICITADO", "ACTIVO", "VENCIDO"],
        ).exists():
            return

        if Reserva.objects.filter(
            ejemplar_asignado=ejemplar,
            estado="DISPONIBLE",
        ).exists():
            return

        siguiente = (
            Reserva.objects.select_for_update()
            .filter(libro_id=ejemplar.libro_id, estado="PENDIENTE")
            .order_by("fecha_reserva", "pk")
            .first()
        )

        if siguiente:
            politica = PoliticaPrestamo.objects.filter(
                tipo_usuario=siguiente.usuario.tipo_usuario
            ).first()

            horas = politica.horas_para_recoger if politica else 48

            siguiente.estado = "DISPONIBLE"
            siguiente.ejemplar_asignado = ejemplar
            siguiente.fecha_expiracion = ahora + timedelta(hours=horas)
            siguiente.save(
                update_fields=[
                    "estado",
                    "ejemplar_asignado",
                    "fecha_expiracion",
                ]
            )

            self.avisar(
                siguiente.usuario_id,
                "RESERVA_DISPONIBLE",
                f"Reserva #{siguiente.pk}: tu ejemplar "
                f"{ejemplar.codigo_inventario} está disponible. "
                f"Tienes {horas} horas para recogerlo.",
            )
        else:
            ejemplar.estado = "DISPONIBLE"
            ejemplar.save(update_fields=["estado"])

    def handle(self, *args, **options):
        hoy = timezone.localdate()
        ahora = timezone.now()

        vencidos = 0
        solicitudes_expiradas = 0
        reservas_expiradas = 0

        # 1. Marcar préstamos vencidos y avisar.
        candidatos = list(
            Prestamo.objects.filter(
                estado__in=["ACTIVO", "VENCIDO"],
                fecha_vencimiento__lt=hoy,
            ).values_list("pk", "usuario_id")
        )

        for prestamo_id, usuario_id in candidatos:
            with transaction.atomic():
                Usuario.objects.select_for_update().get(pk=usuario_id)
                prestamo = Prestamo.objects.select_for_update().get(
                    pk=prestamo_id
                )

                # Volvemos a comprobar por si se devolvió mientras tanto.
                if (
                    prestamo.estado not in ["ACTIVO", "VENCIDO"]
                    or not prestamo.fecha_vencimiento
                    or prestamo.fecha_vencimiento >= hoy
                ):
                    continue

                if prestamo.estado == "ACTIVO":
                    prestamo.estado = "VENCIDO"
                    prestamo.save(update_fields=["estado"])
                    vencidos += 1

                self.avisar(
                    usuario_id,
                    "VENCIDO",
                    f"El préstamo #{prestamo.pk} venció el "
                    f"{prestamo.fecha_vencimiento:%d/%m/%Y}. "
                    "Acude a la biblioteca para devolverlo.",
                )

        # 2. Expirar solicitudes que no se recogieron.
        candidatos = list(
            Prestamo.objects.filter(
                estado="SOLICITADO",
                fecha_limite_recoger__lte=ahora,
            ).values_list("pk", "usuario_id")
        )

        for prestamo_id, usuario_id in candidatos:
            with transaction.atomic():
                Usuario.objects.select_for_update().get(pk=usuario_id)
                prestamo = Prestamo.objects.select_for_update().get(
                    pk=prestamo_id
                )

                if (
                    prestamo.estado != "SOLICITADO"
                    or not prestamo.fecha_limite_recoger
                    or prestamo.fecha_limite_recoger > ahora
                ):
                    continue

                ejemplar = Ejemplar.objects.select_for_update().get(
                    pk=prestamo.ejemplar_id
                )

                prestamo.estado = "EXPIRADO"
                prestamo.save(update_fields=["estado"])
                self.reasignar_ejemplar(ejemplar, ahora)
                solicitudes_expiradas += 1

        # 3. Expirar reservas apartadas cuyo plazo ya terminó.
        candidatos = list(
            Reserva.objects.filter(
                estado="DISPONIBLE",
                fecha_expiracion__lte=ahora,
            ).values_list("pk", "usuario_id")
        )

        for reserva_id, usuario_id in candidatos:
            with transaction.atomic():
                Usuario.objects.select_for_update().get(pk=usuario_id)

                # Primero localizamos el ejemplar para mantener
                # el orden de bloqueo: usuario, ejemplar, reserva.
                datos = Reserva.objects.get(pk=reserva_id)
                ejemplar = None

                if datos.ejemplar_asignado_id:
                    ejemplar = Ejemplar.objects.select_for_update().get(
                        pk=datos.ejemplar_asignado_id
                    )

                reserva = Reserva.objects.select_for_update().get(
                    pk=reserva_id
                )

                if (
                    reserva.estado != "DISPONIBLE"
                    or not reserva.fecha_expiracion
                    or reserva.fecha_expiracion > ahora
                    or reserva.ejemplar_asignado_id
                    != datos.ejemplar_asignado_id
                ):
                    continue

                reserva.estado = "EXPIRADA"
                reserva.save(update_fields=["estado"])

                if ejemplar:
                    self.reasignar_ejemplar(ejemplar, ahora)

                reservas_expiradas += 1

        # 4. Recordar los préstamos que vencen mañana.
        manana = hoy + timedelta(days=1)

        candidatos = list(
            Prestamo.objects.filter(
                estado="ACTIVO",
                fecha_vencimiento=manana,
            ).values_list("pk", "usuario_id")
        )

        for prestamo_id, usuario_id in candidatos:
            with transaction.atomic():
                Usuario.objects.select_for_update().get(pk=usuario_id)
                prestamo = Prestamo.objects.select_for_update().get(
                    pk=prestamo_id
                )

                if (
                    prestamo.estado != "ACTIVO"
                    or prestamo.fecha_vencimiento != manana
                ):
                    continue

                self.avisar(
                    usuario_id,
                    "VENCE_PRONTO",
                    f"El préstamo #{prestamo.pk} vence mañana, "
                    f"{manana:%d/%m/%Y}. Recuerda devolverlo a tiempo.",
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Préstamos marcados vencidos: {vencidos}. "
                f"Solicitudes expiradas: {solicitudes_expiradas}. "
                f"Reservas expiradas: {reservas_expiradas}."
            )
        )