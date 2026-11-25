from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from catalogo.models import Categoria, Editorial, Ejemplar, Libro
from multas.models import Multa
from notificaciones.models import Notificacion
from prestamos.models import PoliticaPrestamo, Prestamo, Reserva


Usuario = get_user_model()


class DevolucionesYReservasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.bibliotecario = Usuario.objects.create_user(
            username="bib_devoluciones",
            tipo_usuario="BIBLIOTECARIO",
        )

        cls.lector = Usuario.objects.create_user(
            username="lector_devoluciones",
            tipo_usuario="ESTUDIANTE",
        )

        cls.primero = Usuario.objects.create_user(
            username="primero_cola",
            tipo_usuario="ESTUDIANTE",
        )

        cls.segundo = Usuario.objects.create_user(
            username="segundo_cola",
            tipo_usuario="ESTUDIANTE",
        )

        PoliticaPrestamo.objects.create(
            tipo_usuario="ESTUDIANTE",
            dias_prestamos=7,
            max_libros=3,
            max_renovaciones=1,
            multa_por_dia=Decimal("10.00"),
            multa_maxima=Decimal("300.00"),
            horas_para_recoger=48,
        )

        categoria = Categoria.objects.create(nombre="Devoluciones")
        editorial = Editorial.objects.create(nombre="Editorial devoluciones")

        cls.libro = Libro.objects.create(
            titulo="Libro para devolver",
            isbn="9780000000100",
            categoria=categoria,
            editorial=editorial,
            costo_reposicion=Decimal("250.00"),
        )

        cls.ejemplar = Ejemplar.objects.create(
            libro=cls.libro,
            codigo_inventario="DEV-001",
            estado="PRESTADO",
        )

        cls.prestamo = Prestamo.objects.create(
            usuario=cls.lector,
            ejemplar=cls.ejemplar,
            estado="ACTIVO",
            fecha_prestamo=timezone.now() - timedelta(days=4),
            fecha_vencimiento=timezone.localdate() + timedelta(days=3),
        )

    def setUp(self):
        self.client.force_login(self.bibliotecario)

    def devolver(self):
        return self.client.post(
            reverse("devolver_prestamo", args=[self.prestamo.pk])
        )

    def poner_retraso(self, dias):
        self.prestamo.fecha_vencimiento = (
            timezone.localdate() - timedelta(days=dias)
        )
        self.prestamo.save(update_fields=["fecha_vencimiento"])

    def crear_cola(self):
        ahora = timezone.now()

        primera = Reserva.objects.create(
            usuario=self.primero,
            libro=self.libro,
            estado="PENDIENTE",
            fecha_reserva=ahora - timedelta(hours=2),
        )

        segunda = Reserva.objects.create(
            usuario=self.segundo,
            libro=self.libro,
            estado="PENDIENTE",
            fecha_reserva=ahora - timedelta(hours=1),
        )

        return primera, segunda

    def preparar_solicitud(self, expirada=False):
        self.prestamo.estado = "SOLICITADO"
        self.prestamo.fecha_prestamo = None
        self.prestamo.fecha_vencimiento = None
        self.prestamo.fecha_limite_recoger = (
            timezone.now()
            + timedelta(hours=-1 if expirada else 48)
        )
        self.prestamo.save()

        self.ejemplar.estado = "RESERVADO"
        self.ejemplar.save(update_fields=["estado"])

    def comprobar_asignacion(self, reserva):
        reserva.refresh_from_db()
        self.ejemplar.refresh_from_db()

        self.assertEqual(reserva.estado, "DISPONIBLE")
        self.assertEqual(
            reserva.ejemplar_asignado_id,
            self.ejemplar.pk,
        )
        self.assertIsNotNone(reserva.fecha_expiracion)
        self.assertEqual(self.ejemplar.estado, "RESERVADO")

        self.assertEqual(
            Notificacion.objects.filter(
                usuario_id=reserva.usuario_id,
                tipo="RESERVA_DISPONIBLE",
            ).count(),
            1,
        )

    def test_devolver_el_dia_del_vencimiento_no_genera_multa(self):
        self.poner_retraso(0)

        respuesta = self.devolver()

        self.assertEqual(respuesta.status_code, 302)

        self.prestamo.refresh_from_db()
        self.ejemplar.refresh_from_db()

        self.assertEqual(self.prestamo.estado, "DEVUELTO")
        self.assertEqual(
            self.prestamo.recibido_por_id,
            self.bibliotecario.pk,
        )
        self.assertIsNotNone(self.prestamo.fecha_devolucion)
        self.assertEqual(self.ejemplar.estado, "DISPONIBLE")
        self.assertFalse(Multa.objects.exists())

    def test_tres_dias_de_retraso_generan_treinta_pesos(self):
        self.poner_retraso(3)
        self.devolver()

        multa = Multa.objects.get(
            prestamo=self.prestamo,
            motivo="RETRASO",
        )

        self.assertEqual(multa.usuario_id, self.lector.pk)
        self.assertEqual(multa.dias_retraso, 3)
        self.assertEqual(multa.monto, Decimal("30.00"))
        self.assertEqual(multa.estado, "PENDIENTE")

    def test_multa_por_retraso_respeta_tope_de_trescientos(self):
        self.poner_retraso(45)
        self.devolver()

        multa = Multa.objects.get(
            prestamo=self.prestamo,
            motivo="RETRASO",
        )

        self.assertEqual(multa.dias_retraso, 45)
        self.assertEqual(multa.monto, Decimal("300.00"))

    def test_devolver_dos_veces_no_duplica_la_multa(self):
        self.poner_retraso(3)

        self.devolver()

        self.prestamo.refresh_from_db()
        fecha_original = self.prestamo.fecha_devolucion

        self.devolver()

        self.prestamo.refresh_from_db()

        self.assertEqual(
            self.prestamo.fecha_devolucion,
            fecha_original,
        )
        self.assertEqual(
            Multa.objects.filter(prestamo=self.prestamo).count(),
            1,
        )

    def test_lector_no_puede_registrar_devolucion(self):
        self.client.force_login(self.lector)

        respuesta = self.devolver()

        self.assertRedirects(
            respuesta,
            reverse("home"),
            fetch_redirect_response=False,
        )

        self.prestamo.refresh_from_db()
        self.ejemplar.refresh_from_db()

        self.assertEqual(self.prestamo.estado, "ACTIVO")
        self.assertIsNone(self.prestamo.fecha_devolucion)
        self.assertEqual(self.ejemplar.estado, "PRESTADO")
        self.assertFalse(Multa.objects.exists())

    def test_devolucion_asigna_al_primero_de_la_cola(self):
        primera, segunda = self.crear_cola()
        antes = timezone.now()

        self.devolver()

        self.comprobar_asignacion(primera)
        segunda.refresh_from_db()

        self.assertEqual(segunda.estado, "PENDIENTE")
        self.assertIsNone(segunda.ejemplar_asignado_id)

        self.assertGreaterEqual(
            primera.fecha_expiracion,
            antes + timedelta(hours=48),
        )
        self.assertLessEqual(
            primera.fecha_expiracion,
            timezone.now() + timedelta(hours=48),
        )

    def test_cancelar_reserva_asignada_atiende_al_siguiente(self):
        primera, segunda = self.crear_cola()

        self.devolver()

        self.client.force_login(self.primero)

        respuesta = self.client.post(
            reverse("cancelar_reserva", args=[primera.pk])
        )

        self.assertEqual(respuesta.status_code, 302)

        primera.refresh_from_db()
        self.assertEqual(primera.estado, "CANCELADA")
        self.comprobar_asignacion(segunda)

    def test_cancelar_solicitud_atiende_la_cola(self):
        self.preparar_solicitud()
        primera, segunda = self.crear_cola()

        self.client.force_login(self.lector)

        respuesta = self.client.post(
            reverse(
                "cancelar_solicitud",
                args=[self.prestamo.pk],
            )
        )

        self.assertEqual(respuesta.status_code, 302)

        self.prestamo.refresh_from_db()
        segunda.refresh_from_db()

        self.assertEqual(self.prestamo.estado, "CANCELADO")
        self.comprobar_asignacion(primera)
        self.assertEqual(segunda.estado, "PENDIENTE")

    def test_danio_genera_reposicion_y_retraso_sin_asignar_reserva(self):
        self.poner_retraso(3)
        primera, segunda = self.crear_cola()

        respuesta = self.client.post(
            reverse(
                "registrar_incidencia",
                args=[self.prestamo.pk],
            ),
            {
                "tipo": "DANIO",
                "descripcion": "Portada y hojas dañadas.",
                "monto": "0.01",
            },
        )

        self.assertEqual(respuesta.status_code, 302)

        self.prestamo.refresh_from_db()
        self.ejemplar.refresh_from_db()

        self.assertEqual(self.prestamo.estado, "DEVUELTO")
        self.assertEqual(self.ejemplar.estado, "EN_REPARACION")

        # El costo proviene del libro, no del monto enviado.
        self.assertEqual(
            Multa.objects.get(
                prestamo=self.prestamo,
                motivo="DANIO",
            ).monto,
            Decimal("250.00"),
        )

        self.assertEqual(
            Multa.objects.get(
                prestamo=self.prestamo,
                motivo="RETRASO",
            ).monto,
            Decimal("30.00"),
        )

        for reserva in (primera, segunda):
            reserva.refresh_from_db()
            self.assertEqual(reserva.estado, "PENDIENTE")
            self.assertIsNone(reserva.ejemplar_asignado_id)

    def test_perdida_no_registra_devolucion_fisica(self):
        respuesta = self.client.post(
            reverse(
                "registrar_incidencia",
                args=[self.prestamo.pk],
            ),
            {
                "tipo": "PERDIDA",
                "descripcion": "El lector reporta el ejemplar perdido.",
            },
        )

        self.assertEqual(respuesta.status_code, 302)

        self.prestamo.refresh_from_db()
        self.ejemplar.refresh_from_db()

        self.assertEqual(self.prestamo.estado, "PERDIDO")
        self.assertEqual(self.ejemplar.estado, "PERDIDO")
        self.assertIsNone(self.prestamo.fecha_devolucion)
        self.assertIsNone(self.prestamo.recibido_por_id)

        multa = Multa.objects.get(
            prestamo=self.prestamo,
            motivo="PERDIDA",
        )

        self.assertEqual(multa.monto, Decimal("250.00"))
        self.assertEqual(multa.estado, "PENDIENTE")

    def test_comando_marca_vencido_sin_duplicar_aviso(self):
        self.poner_retraso(1)

        for _ in range(2):
            call_command(
                "procesar_vencimientos",
                stdout=StringIO(),
            )

        self.prestamo.refresh_from_db()

        self.assertEqual(self.prestamo.estado, "VENCIDO")
        self.assertEqual(
            Notificacion.objects.filter(
                usuario=self.lector,
                tipo="VENCIDO",
            ).count(),
            1,
        )

        # La multa se calcula al cerrar el préstamo.
        self.assertFalse(Multa.objects.exists())

    def test_comando_expira_solicitud_y_asigna_reserva(self):
        self.preparar_solicitud(expirada=True)
        primera, segunda = self.crear_cola()

        call_command(
            "procesar_vencimientos",
            stdout=StringIO(),
        )

        self.prestamo.refresh_from_db()
        segunda.refresh_from_db()

        self.assertEqual(self.prestamo.estado, "EXPIRADO")
        self.comprobar_asignacion(primera)
        self.assertEqual(segunda.estado, "PENDIENTE")

    def test_comando_expira_reserva_y_atiende_al_siguiente(self):
        primera, segunda = self.crear_cola()

        self.devolver()

        primera.refresh_from_db()
        primera.fecha_expiracion = (
            timezone.now() - timedelta(minutes=1)
        )
        primera.save(update_fields=["fecha_expiracion"])

        call_command(
            "procesar_vencimientos",
            stdout=StringIO(),
        )

        primera.refresh_from_db()

        self.assertEqual(primera.estado, "EXPIRADA")
        self.comprobar_asignacion(segunda)