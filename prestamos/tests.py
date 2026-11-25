from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from catalogo.models import Categoria, Editorial, Ejemplar, Libro
from multas.models import Multa
from prestamos.models import PoliticaPrestamo, Prestamo, Reserva


Usuario = get_user_model()


class SolicitudesPrestamoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.estudiante = Usuario.objects.create_user(
            username="estudiante_test",
            tipo_usuario="ESTUDIANTE",
        )

        cls.otro_lector = Usuario.objects.create_user(
            username="otro_test",
            tipo_usuario="ESTUDIANTE",
        )

        cls.bibliotecario = Usuario.objects.create_user(
            username="bibliotecario_test",
            tipo_usuario="BIBLIOTECARIO",
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

        cls.categoria = Categoria.objects.create(
            nombre="Categoría de prueba",
        )

        cls.editorial = Editorial.objects.create(
            nombre="Editorial de prueba",
        )

        cls.libro = Libro.objects.create(
            titulo="Libro de prueba",
            isbn="9780000000001",
            categoria=cls.categoria,
            editorial=cls.editorial,
            costo_reposicion=Decimal("250.00"),
        )

        cls.ejemplar = Ejemplar.objects.create(
            libro=cls.libro,
            codigo_inventario="TEST-001",
            estado="DISPONIBLE",
        )

    def setUp(self):
        self.client.force_login(self.estudiante)

        self.url = reverse(
            "solicitar_prestamo",
            args=[self.libro.pk],
        )

        self.contador = 0

    def crear_otro_prestamo(self, vencido=False):
        self.contador += 1

        libro = Libro.objects.create(
            titulo=f"Otro libro {self.contador}",
            isbn=f"979{self.contador:010d}",
            categoria=self.categoria,
            editorial=self.editorial,
        )

        ejemplar = Ejemplar.objects.create(
            libro=libro,
            codigo_inventario=f"OTRO-{self.contador}",
            estado="PRESTADO",
        )

        return Prestamo.objects.create(
            usuario=self.estudiante,
            ejemplar=ejemplar,
            estado="ACTIVO",
            fecha_prestamo=timezone.now() - timedelta(days=8),
            fecha_vencimiento=(
                timezone.localdate()
                + timedelta(days=-1 if vencido else 7)
            ),
        )

    def comprobar_rechazo(self):
        cantidad_anterior = Prestamo.objects.count()

        respuesta = self.client.post(self.url)

        self.assertIn(respuesta.status_code, (302, 403, 404))
        self.assertEqual(
            Prestamo.objects.count(),
            cantidad_anterior,
        )

        self.ejemplar.refresh_from_db()
        self.assertEqual(self.ejemplar.estado, "DISPONIBLE")

    def test_solicitud_valida_reserva_el_ejemplar_por_48_horas(self):
        antes = timezone.now()

        respuesta = self.client.post(self.url)

        self.assertEqual(respuesta.status_code, 302)

        prestamo = Prestamo.objects.get(
            usuario=self.estudiante,
            ejemplar=self.ejemplar,
        )

        self.assertEqual(prestamo.estado, "SOLICITADO")
        self.assertIsNone(prestamo.fecha_prestamo)
        self.assertIsNone(prestamo.fecha_vencimiento)

        self.assertGreaterEqual(
            prestamo.fecha_limite_recoger,
            antes + timedelta(hours=48),
        )

        self.assertLessEqual(
            prestamo.fecha_limite_recoger,
            timezone.now() + timedelta(hours=48),
        )

        self.ejemplar.refresh_from_db()
        self.assertEqual(self.ejemplar.estado, "RESERVADO")

    def test_get_no_crea_solicitudes(self):
        respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.status_code, 405)
        self.assertFalse(Prestamo.objects.exists())

        self.ejemplar.refresh_from_db()
        self.assertEqual(self.ejemplar.estado, "DISPONIBLE")

    def test_usuario_sin_sesion_no_puede_solicitar(self):
        self.client.logout()

        respuesta = self.client.post(self.url)

        self.assertEqual(respuesta.status_code, 302)
        self.assertFalse(Prestamo.objects.exists())

        self.ejemplar.refresh_from_db()
        self.assertEqual(self.ejemplar.estado, "DISPONIBLE")

    def test_bibliotecario_no_puede_solicitar_como_lector(self):
        self.client.force_login(self.bibliotecario)
        self.comprobar_rechazo()

    def test_libro_inactivo_no_admite_solicitudes(self):
        self.libro.activo = False
        self.libro.save(update_fields=["activo"])

        self.comprobar_rechazo()

    def test_usuario_bloqueado_no_puede_solicitar(self):
        self.estudiante.bloqueado = True
        self.estudiante.save(update_fields=["bloqueado"])

        self.comprobar_rechazo()

    def test_multa_pendiente_impide_solicitar(self):
        anterior = self.crear_otro_prestamo()

        Multa.objects.create(
            prestamo=anterior,
            usuario=self.estudiante,
            motivo="RETRASO",
            dias_retraso=1,
            monto=Decimal("10.00"),
            estado="PENDIENTE",
        )

        self.comprobar_rechazo()

    def test_detecta_fecha_vencida_aunque_siga_activo(self):
        # No depende de haber ejecutado procesar_vencimientos.
        self.crear_otro_prestamo(vencido=True)

        self.comprobar_rechazo()

    def test_estudiante_con_tres_prestamos_no_puede_pedir_otro(self):
        for _ in range(3):
            self.crear_otro_prestamo()

        self.comprobar_rechazo()

    def test_no_permite_otro_prestamo_del_mismo_titulo(self):
        ocupado = Ejemplar.objects.create(
            libro=self.libro,
            codigo_inventario="MISMO-TITULO",
            estado="PRESTADO",
        )

        Prestamo.objects.create(
            usuario=self.estudiante,
            ejemplar=ocupado,
            estado="ACTIVO",
            fecha_prestamo=timezone.now(),
            fecha_vencimiento=(
                timezone.localdate() + timedelta(days=7)
            ),
        )

        self.comprobar_rechazo()

    def test_respeta_la_cola_de_reservas_pendientes(self):
        # Comprueba que una disponibilidad no permita saltarse la cola.
        Reserva.objects.create(
            usuario=self.otro_lector,
            libro=self.libro,
            estado="PENDIENTE",
        )

        self.comprobar_rechazo()

    def test_no_solicita_ejemplares_no_disponibles(self):
        for estado in (
            "RESERVADO",
            "PRESTADO",
            "EN_REPARACION",
            "PERDIDO",
            "BAJA",
        ):
            with self.subTest(estado=estado):
                self.ejemplar.estado = estado
                self.ejemplar.save(update_fields=["estado"])

                respuesta = self.client.post(self.url)

                self.assertEqual(respuesta.status_code, 302)
                self.assertFalse(Prestamo.objects.exists())

                self.ejemplar.refresh_from_db()
                self.assertEqual(self.ejemplar.estado, estado)
class RenovacionesYPermisosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.estudiante = Usuario.objects.create_user(
            username="lector_renovacion",
            tipo_usuario="ESTUDIANTE",
        )

        cls.profesor = Usuario.objects.create_user(
            username="profesor_renovacion",
            tipo_usuario="PROFESOR",
        )

        cls.otro_lector = Usuario.objects.create_user(
            username="lector_ajeno",
            tipo_usuario="ESTUDIANTE",
        )

        cls.bibliotecario = Usuario.objects.create_user(
            username="bibliotecario_permisos",
            tipo_usuario="BIBLIOTECARIO",
        )

        for tipo, dias, maximo, renovaciones in (
            ("ESTUDIANTE", 7, 3, 1),
            ("PROFESOR", 30, 10, 2),
        ):
            PoliticaPrestamo.objects.create(
                tipo_usuario=tipo,
                dias_prestamos=dias,
                max_libros=maximo,
                max_renovaciones=renovaciones,
                multa_por_dia=Decimal("10.00"),
                multa_maxima=Decimal("300.00"),
                horas_para_recoger=48,
            )

        cls.categoria = Categoria.objects.create(
            nombre="Categoría renovaciones",
        )

        cls.editorial = Editorial.objects.create(
            nombre="Editorial renovaciones",
        )

    def setUp(self):
        self.client.force_login(self.estudiante)
        self.contador = 0

    def crear_prestamo(self, usuario=None, dias=3):
        self.contador += 1

        libro = Libro.objects.create(
            titulo=f"Libro renovación {self.contador}",
            isbn=f"980{self.contador:010d}",
            categoria=self.categoria,
            editorial=self.editorial,
        )

        ejemplar = Ejemplar.objects.create(
            libro=libro,
            codigo_inventario=f"REN-{self.contador}",
            estado="PRESTADO",
        )

        return Prestamo.objects.create(
            usuario=usuario or self.estudiante,
            ejemplar=ejemplar,
            estado="ACTIVO",
            fecha_prestamo=timezone.now() - timedelta(days=2),
            fecha_vencimiento=(
                timezone.localdate() + timedelta(days=dias)
            ),
        )

    def renovar(self, prestamo):
        return self.client.post(
            reverse("renovar_prestamo", args=[prestamo.pk])
        )

    def comprobar_renovacion_rechazada(self, prestamo):
        fecha_anterior = prestamo.fecha_vencimiento
        contador_anterior = prestamo.num_renovaciones

        respuesta = self.renovar(prestamo)

        self.assertEqual(respuesta.status_code, 302)

        prestamo.refresh_from_db()

        self.assertEqual(
            prestamo.fecha_vencimiento,
            fecha_anterior,
        )
        self.assertEqual(
            prestamo.num_renovaciones,
            contador_anterior,
        )

    def test_renovacion_estudiante_cuenta_siete_dias_desde_hoy(self):
        prestamo = self.crear_prestamo()

        respuesta = self.renovar(prestamo)

        self.assertEqual(respuesta.status_code, 302)

        prestamo.refresh_from_db()

        self.assertEqual(prestamo.num_renovaciones, 1)
        self.assertEqual(
            prestamo.fecha_vencimiento,
            timezone.localdate() + timedelta(days=7),
        )

    def test_estudiante_no_puede_renovar_dos_veces(self):
        prestamo = self.crear_prestamo()

        self.renovar(prestamo)
        prestamo.refresh_from_db()

        self.assertEqual(prestamo.num_renovaciones, 1)
        self.comprobar_renovacion_rechazada(prestamo)

    def test_profesor_puede_renovar_dos_veces_pero_no_tres(self):
        self.client.force_login(self.profesor)
        prestamo = self.crear_prestamo(usuario=self.profesor)

        for numero in (1, 2):
            self.renovar(prestamo)
            prestamo.refresh_from_db()

            self.assertEqual(prestamo.num_renovaciones, numero)
            self.assertEqual(
                prestamo.fecha_vencimiento,
                timezone.localdate() + timedelta(days=30),
            )

        self.comprobar_renovacion_rechazada(prestamo)

    def test_no_renueva_prestamo_con_fecha_vencida(self):
        prestamo = self.crear_prestamo(dias=-1)
        self.comprobar_renovacion_rechazada(prestamo)

    def test_otro_prestamo_atrasado_impide_renovar(self):
        prestamo = self.crear_prestamo()
        self.crear_prestamo(dias=-1)

        self.comprobar_renovacion_rechazada(prestamo)

    def test_cuenta_bloqueada_no_puede_renovar(self):
        prestamo = self.crear_prestamo()

        self.estudiante.bloqueado = True
        self.estudiante.save(update_fields=["bloqueado"])

        self.comprobar_renovacion_rechazada(prestamo)

    def test_multa_pendiente_impide_renovar(self):
        prestamo = self.crear_prestamo()

        Multa.objects.create(
            prestamo=prestamo,
            usuario=self.estudiante,
            motivo="RETRASO",
            dias_retraso=1,
            monto=Decimal("10.00"),
            estado="PENDIENTE",
        )

        self.comprobar_renovacion_rechazada(prestamo)

    def test_reserva_de_otro_lector_impide_renovar(self):
        prestamo = self.crear_prestamo()

        Reserva.objects.create(
            usuario=self.otro_lector,
            libro=prestamo.ejemplar.libro,
            estado="PENDIENTE",
        )

        self.comprobar_renovacion_rechazada(prestamo)

    def test_no_puede_renovar_prestamo_ajeno(self):
        prestamo = self.crear_prestamo(usuario=self.otro_lector)
        fecha_anterior = prestamo.fecha_vencimiento

        respuesta = self.renovar(prestamo)

        self.assertEqual(respuesta.status_code, 404)

        prestamo.refresh_from_db()

        self.assertEqual(prestamo.num_renovaciones, 0)
        self.assertEqual(
            prestamo.fecha_vencimiento,
            fecha_anterior,
        )

    def test_get_no_renueva_prestamos(self):
        prestamo = self.crear_prestamo()

        respuesta = self.client.get(
            reverse("renovar_prestamo", args=[prestamo.pk])
        )

        self.assertEqual(respuesta.status_code, 405)

        prestamo.refresh_from_db()
        self.assertEqual(prestamo.num_renovaciones, 0)

    def test_historial_solo_muestra_prestamos_propios(self):
        propio = self.crear_prestamo()
        self.crear_prestamo(usuario=self.otro_lector)

        respuesta = self.client.get(reverse("mis_prestamos"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            set(
                respuesta.context["prestamos"].values_list(
                    "pk",
                    flat=True,
                )
            ),
            {propio.pk},
        )

    def test_lector_no_puede_registrar_entrega(self):
        prestamo = self.crear_prestamo()

        prestamo.estado = "SOLICITADO"
        prestamo.fecha_prestamo = None
        prestamo.fecha_vencimiento = None
        prestamo.fecha_limite_recoger = (
            timezone.now() + timedelta(hours=48)
        )
        prestamo.save()

        ejemplar = prestamo.ejemplar
        ejemplar.estado = "RESERVADO"
        ejemplar.save(update_fields=["estado"])

        respuesta = self.client.post(
            reverse("entregar_prestamo", args=[prestamo.pk])
        )

        self.assertRedirects(
            respuesta,
            reverse("home"),
            fetch_redirect_response=False,
        )

        prestamo.refresh_from_db()
        ejemplar.refresh_from_db()

        self.assertEqual(prestamo.estado, "SOLICITADO")
        self.assertIsNone(prestamo.entregado_por_id)
        self.assertEqual(ejemplar.estado, "RESERVADO")

    def test_renovacion_requiere_token_csrf(self):
        from django.test import Client

        prestamo = self.crear_prestamo()
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.estudiante)

        respuesta = cliente.post(
            reverse("renovar_prestamo", args=[prestamo.pk])
        )

        self.assertEqual(respuesta.status_code, 403)

        prestamo.refresh_from_db()
        self.assertEqual(prestamo.num_renovaciones, 0)
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.db import close_old_connections, connections
from django.test import Client, TransactionTestCase, skipUnlessDBFeature


@skipUnlessDBFeature("has_select_for_update")
class SolicitudesConcurrentesTests(TransactionTestCase):
    def setUp(self):
        self.lector1 = Usuario.objects.create_user(
            username="concurrente_1",
            tipo_usuario="ESTUDIANTE",
        )

        self.lector2 = Usuario.objects.create_user(
            username="concurrente_2",
            tipo_usuario="ESTUDIANTE",
        )

        self.politica = PoliticaPrestamo.objects.create(
            tipo_usuario="ESTUDIANTE",
            dias_prestamos=7,
            max_libros=3,
            max_renovaciones=1,
            multa_por_dia=Decimal("10.00"),
            multa_maxima=Decimal("300.00"),
            horas_para_recoger=48,
        )

        self.categoria = Categoria.objects.create(
            nombre="Concurrencia",
        )

        self.editorial = Editorial.objects.create(
            nombre="Editorial concurrencia",
        )

        self.libro1, self.ejemplar1 = self.crear_libro(1)
        self.libro2, self.ejemplar2 = self.crear_libro(2)

    def crear_libro(self, numero):
        libro = Libro.objects.create(
            titulo=f"Libro concurrente {numero}",
            isbn=f"981{numero:010d}",
            categoria=self.categoria,
            editorial=self.editorial,
        )

        ejemplar = Ejemplar.objects.create(
            libro=libro,
            codigo_inventario=f"CONC-{numero}",
            estado="DISPONIBLE",
        )

        return libro, ejemplar

    def ejecutar_simultaneamente(self, operaciones):
        # Cada petición utiliza su propio cliente y conexión.
        clientes = []

        for usuario, libro in operaciones:
            cliente = Client()
            cliente.force_login(usuario)
            clientes.append((cliente, libro.pk))

        barrera = Barrier(len(clientes))

        def solicitar(cliente, libro_id):
            close_old_connections()

            try:
                barrera.wait(timeout=10)

                respuesta = cliente.post(
                    reverse(
                        "solicitar_prestamo",
                        args=[libro_id],
                    )
                )

                return respuesta.status_code
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=len(clientes)) as ejecutor:
            futuros = [
                ejecutor.submit(solicitar, cliente, libro_id)
                for cliente, libro_id in clientes
            ]

            resultados = [
                futuro.result(timeout=30)
                for futuro in futuros
            ]

        self.assertEqual(resultados, [302] * len(clientes))

    def test_dos_lectores_no_apartan_el_mismo_ejemplar(self):
        self.ejecutar_simultaneamente(
            [
                (self.lector1, self.libro1),
                (self.lector2, self.libro1),
            ]
        )

        solicitudes = Prestamo.objects.filter(
            ejemplar=self.ejemplar1,
            estado="SOLICITADO",
        )

        self.assertEqual(solicitudes.count(), 1)
        self.assertEqual(Prestamo.objects.count(), 1)

        self.ejemplar1.refresh_from_db()
        self.assertEqual(self.ejemplar1.estado, "RESERVADO")

    def test_dos_solicitudes_no_superan_el_ultimo_cupo(self):
        self.politica.max_libros = 1
        self.politica.save(update_fields=["max_libros"])

        self.ejecutar_simultaneamente(
            [
                (self.lector1, self.libro1),
                (self.lector1, self.libro2),
            ]
        )

        solicitudes = Prestamo.objects.filter(
            usuario=self.lector1,
            estado="SOLICITADO",
        )

        self.assertEqual(solicitudes.count(), 1)
        self.assertEqual(Prestamo.objects.count(), 1)

        self.ejemplar1.refresh_from_db()
        self.ejemplar2.refresh_from_db()

        self.assertCountEqual(
            [self.ejemplar1.estado, self.ejemplar2.estado],
            ["RESERVADO", "DISPONIBLE"],
        )