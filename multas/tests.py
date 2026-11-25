from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from catalogo.models import Categoria, Editorial, Ejemplar, Libro
from multas.models import Multa, Pago
from prestamos.models import Prestamo


Usuario = get_user_model()


class PagosYCondonacionesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.bibliotecario = Usuario.objects.create_user(
            username="bib_multas",
            tipo_usuario="BIBLIOTECARIO",
        )

        cls.lector = Usuario.objects.create_user(
            username="lector_multas",
            tipo_usuario="ESTUDIANTE",
        )

        cls.otro_lector = Usuario.objects.create_user(
            username="otro_multas",
            tipo_usuario="ESTUDIANTE",
        )

        categoria = Categoria.objects.create(nombre="Multas")
        editorial = Editorial.objects.create(nombre="Editorial multas")

        libro = Libro.objects.create(
            titulo="Libro multas",
            isbn="9780000000200",
            categoria=categoria,
            editorial=editorial,
        )

        ejemplar = Ejemplar.objects.create(
            libro=libro,
            codigo_inventario="MULTA-001",
            estado="DISPONIBLE",
        )

        cls.prestamo = Prestamo.objects.create(
            usuario=cls.lector,
            ejemplar=ejemplar,
            estado="DEVUELTO",
            fecha_prestamo=timezone.now() - timedelta(days=10),
            fecha_vencimiento=timezone.localdate() - timedelta(days=3),
            fecha_devolucion=timezone.now(),
        )

        prestamo_ajeno = Prestamo.objects.create(
            usuario=cls.otro_lector,
            ejemplar=ejemplar,
            estado="DEVUELTO",
            fecha_prestamo=timezone.now() - timedelta(days=10),
            fecha_vencimiento=timezone.localdate() - timedelta(days=3),
            fecha_devolucion=timezone.now(),
        )

        cls.multa = Multa.objects.create(
            prestamo=cls.prestamo,
            usuario=cls.lector,
            motivo="RETRASO",
            dias_retraso=3,
            monto=Decimal("30.00"),
            estado="PENDIENTE",
        )

        cls.multa_ajena = Multa.objects.create(
            prestamo=prestamo_ajeno,
            usuario=cls.otro_lector,
            motivo="RETRASO",
            dias_retraso=9,
            monto=Decimal("90.00"),
            estado="PENDIENTE",
        )

    def setUp(self):
        self.client.force_login(self.bibliotecario)

        self.url_pago = reverse(
            "registrar_pago",
            args=[self.multa.pk],
        )

        self.url_condonar = reverse(
            "condonar_multa",
            args=[self.multa.pk],
        )

    def pagar(self, **datos):
        contenido = {"metodo": "EFECTIVO"}
        contenido.update(datos)
        return self.client.post(self.url_pago, contenido)

    def condonar(self, justificacion="Error administrativo comprobado."):
        return self.client.post(
            self.url_condonar,
            {"justificacion": justificacion},
        )

    def registrar_pago_previo(self, monto=Decimal("10.00")):
        return Pago.objects.create(
            multa=self.multa,
            monto=monto,
            metodo="EFECTIVO",
            folio_recibo="PREVIO-001",
            registrado_por=self.bibliotecario,
        )

    def test_pago_utiliza_saldo_real_y_registra_bibliotecario(self):
        respuesta = self.pagar(monto="0.01")

        self.assertEqual(respuesta.status_code, 302)

        self.multa.refresh_from_db()
        pago = Pago.objects.get(multa=self.multa)

        self.assertEqual(self.multa.estado, "PAGADA")
        self.assertEqual(pago.monto, Decimal("30.00"))
        self.assertEqual(pago.metodo, "EFECTIVO")
        self.assertEqual(
            pago.registrado_por_id,
            self.bibliotecario.pk,
        )
        self.assertTrue(pago.folio_recibo)
        self.assertLessEqual(len(pago.folio_recibo), 30)

    def test_acepta_los_tres_metodos_y_genera_folios_distintos(self):
        folios = []

        for metodo in ("EFECTIVO", "TARJETA", "TRANSFERENCIA"):
            with self.subTest(metodo=metodo):
                multa = Multa.objects.create(
                    prestamo=self.prestamo,
                    usuario=self.lector,
                    motivo="RETRASO",
                    monto=Decimal("10.00"),
                )

                respuesta = self.client.post(
                    reverse("registrar_pago", args=[multa.pk]),
                    {"metodo": metodo},
                )

                self.assertEqual(respuesta.status_code, 302)

                pago = Pago.objects.get(multa=multa)
                self.assertEqual(pago.metodo, metodo)
                folios.append(pago.folio_recibo)

        self.assertEqual(len(set(folios)), 3)

    def test_get_del_formulario_no_registra_pago(self):
        respuesta = self.client.get(self.url_pago)

        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(Pago.objects.exists())

        self.multa.refresh_from_db()
        self.assertEqual(self.multa.estado, "PENDIENTE")

    def test_segundo_intento_no_duplica_el_pago(self):
        self.pagar()

        pago_original = Pago.objects.get(multa=self.multa)

        self.pagar()

        self.assertEqual(
            Pago.objects.filter(multa=self.multa).count(),
            1,
        )
        self.assertEqual(
            Pago.objects.get(multa=self.multa).folio_recibo,
            pago_original.folio_recibo,
        )

    def test_metodo_invalido_no_registra_pago(self):
        respuesta = self.pagar(metodo="INVALIDO")

        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.context["form"].errors)
        self.assertFalse(Pago.objects.exists())

        self.multa.refresh_from_db()
        self.assertEqual(self.multa.estado, "PENDIENTE")

    def test_pago_descuenta_importes_previamente_registrados(self):
        anterior = self.registrar_pago_previo()

        self.pagar()

        nuevo = Pago.objects.filter(
            multa=self.multa,
        ).exclude(pk=anterior.pk).get()

        self.assertEqual(nuevo.monto, Decimal("20.00"))

        self.multa.refresh_from_db()
        self.assertEqual(self.multa.estado, "PAGADA")

        self.assertEqual(
            sum(
                Pago.objects.filter(
                    multa=self.multa,
                ).values_list("monto", flat=True),
                Decimal("0.00"),
            ),
            Decimal("30.00"),
        )

    def test_no_cobra_una_multa_condonada(self):
        self.multa.estado = "CONDONADA"
        self.multa.save(update_fields=["estado"])

        self.pagar()

        self.multa.refresh_from_db()

        self.assertEqual(self.multa.estado, "CONDONADA")
        self.assertFalse(Pago.objects.exists())

    def test_lector_no_puede_registrar_pagos(self):
        self.client.force_login(self.lector)

        respuesta = self.pagar()

        self.assertRedirects(
            respuesta,
            reverse("home"),
            fetch_redirect_response=False,
        )

        self.multa.refresh_from_db()
        self.assertEqual(self.multa.estado, "PENDIENTE")
        self.assertFalse(Pago.objects.exists())

    def test_mis_multas_solo_muestra_las_propias_y_suma_pendientes(self):
        pagada = Multa.objects.create(
            prestamo=self.prestamo,
            usuario=self.lector,
            motivo="DANIO",
            monto=Decimal("100.00"),
            estado="PAGADA",
        )

        condonada = Multa.objects.create(
            prestamo=self.prestamo,
            usuario=self.lector,
            motivo="PERDIDA",
            monto=Decimal("200.00"),
            estado="CONDONADA",
        )

        self.client.force_login(self.lector)

        respuesta = self.client.get(reverse("mis_multas"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            set(
                respuesta.context["multas"].values_list(
                    "pk",
                    flat=True,
                )
            ),
            {self.multa.pk, pagada.pk, condonada.pk},
        )
        self.assertEqual(
            respuesta.context["total_pendiente"],
            Decimal("30.00"),
        )

    def test_condonacion_guarda_motivo_y_bibliotecario(self):
        motivo = "Cobro generado por un error administrativo."

        respuesta = self.condonar(motivo)

        self.assertEqual(respuesta.status_code, 302)

        self.multa.refresh_from_db()

        self.assertEqual(self.multa.estado, "CONDONADA")
        self.assertEqual(
            self.multa.justificacion_condonacion,
            motivo,
        )
        self.assertEqual(
            self.multa.condonada_por_id,
            self.bibliotecario.pk,
        )
        self.assertFalse(Pago.objects.exists())

    def test_no_condona_sin_justificacion(self):
        respuesta = self.condonar("   ")

        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.context["form"].errors)

        self.multa.refresh_from_db()

        self.assertEqual(self.multa.estado, "PENDIENTE")
        self.assertIsNone(self.multa.condonada_por_id)

    def test_no_condona_con_justificacion_mayor_a_255(self):
        respuesta = self.condonar("X" * 256)

        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.context["form"].errors)

        self.multa.refresh_from_db()
        self.assertEqual(self.multa.estado, "PENDIENTE")

    def test_no_condona_multa_pagada(self):
        self.registrar_pago_previo(monto=Decimal("30.00"))

        self.multa.estado = "PAGADA"
        self.multa.save(update_fields=["estado"])

        self.condonar()

        self.multa.refresh_from_db()

        self.assertEqual(self.multa.estado, "PAGADA")
        self.assertIsNone(self.multa.condonada_por_id)
        self.assertEqual(Pago.objects.count(), 1)

    def test_no_condona_multa_con_pago_parcial(self):
        self.registrar_pago_previo()

        self.condonar()

        self.multa.refresh_from_db()

        self.assertEqual(self.multa.estado, "PENDIENTE")
        self.assertIsNone(self.multa.condonada_por_id)
        self.assertEqual(Pago.objects.count(), 1)

    def test_segunda_condonacion_no_reemplaza_la_justificacion(self):
        self.condonar("Primera justificación válida.")
        self.condonar("Intento de reemplazo.")

        self.multa.refresh_from_db()

        self.assertEqual(self.multa.estado, "CONDONADA")
        self.assertEqual(
            self.multa.justificacion_condonacion,
            "Primera justificación válida.",
        )

    def test_lector_no_puede_condonar(self):
        self.client.force_login(self.lector)

        respuesta = self.condonar()

        self.assertRedirects(
            respuesta,
            reverse("home"),
            fetch_redirect_response=False,
        )

        self.multa.refresh_from_db()

        self.assertEqual(self.multa.estado, "PENDIENTE")
        self.assertIsNone(self.multa.condonada_por_id)

    def test_get_del_formulario_no_condona(self):
        respuesta = self.client.get(self.url_condonar)

        self.assertEqual(respuesta.status_code, 200)

        self.multa.refresh_from_db()

        self.assertEqual(self.multa.estado, "PENDIENTE")
        self.assertIsNone(self.multa.condonada_por_id)

    def test_pago_y_condonacion_requieren_csrf(self):
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.bibliotecario)

        for url, datos in (
            (self.url_pago, {"metodo": "EFECTIVO"}),
            (self.url_condonar, {"justificacion": "Motivo válido."}),
        ):
            with self.subTest(url=url):
                respuesta = cliente.post(url, datos)
                self.assertEqual(respuesta.status_code, 403)

        self.multa.refresh_from_db()

        self.assertEqual(self.multa.estado, "PENDIENTE")
        self.assertFalse(Pago.objects.exists())
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.db import close_old_connections, connections
from django.test import TransactionTestCase, skipUnlessDBFeature


@skipUnlessDBFeature("has_select_for_update")
class MultasConcurrentesTests(TransactionTestCase):
    def setUp(self):
        self.bibliotecario1 = Usuario.objects.create_user(
            username="bib_concurrente_1",
            tipo_usuario="BIBLIOTECARIO",
        )

        self.bibliotecario2 = Usuario.objects.create_user(
            username="bib_concurrente_2",
            tipo_usuario="BIBLIOTECARIO",
        )

        lector = Usuario.objects.create_user(
            username="lector_cobro_concurrente",
            tipo_usuario="ESTUDIANTE",
        )

        categoria = Categoria.objects.create(
            nombre="Cobros concurrentes",
        )
        editorial = Editorial.objects.create(
            nombre="Editorial cobros concurrentes",
        )

        libro = Libro.objects.create(
            titulo="Libro cobro concurrente",
            isbn="9780000000300",
            categoria=categoria,
            editorial=editorial,
        )

        ejemplar = Ejemplar.objects.create(
            libro=libro,
            codigo_inventario="COBRO-001",
            estado="DISPONIBLE",
        )

        prestamo = Prestamo.objects.create(
            usuario=lector,
            ejemplar=ejemplar,
            estado="DEVUELTO",
            fecha_prestamo=timezone.now() - timedelta(days=10),
            fecha_vencimiento=timezone.localdate() - timedelta(days=3),
            fecha_devolucion=timezone.now(),
        )

        self.multa = Multa.objects.create(
            prestamo=prestamo,
            usuario=lector,
            motivo="RETRASO",
            dias_retraso=3,
            monto=Decimal("30.00"),
            estado="PENDIENTE",
        )

        self.url_pago = reverse(
            "registrar_pago",
            args=[self.multa.pk],
        )
        self.url_condonar = reverse(
            "condonar_multa",
            args=[self.multa.pk],
        )

    def ejecutar_simultaneamente(self, operaciones):
        peticiones = []

        for usuario, url, datos in operaciones:
            cliente = Client()
            cliente.force_login(usuario)
            peticiones.append((cliente, url, datos))

        barrera = Barrier(len(peticiones))

        def enviar(cliente, url, datos):
            close_old_connections()

            try:
                barrera.wait(timeout=10)
                return cliente.post(url, datos).status_code
            finally:
                connections.close_all()

        with ThreadPoolExecutor(
            max_workers=len(peticiones)
        ) as ejecutor:
            futuros = [
                ejecutor.submit(enviar, cliente, url, datos)
                for cliente, url, datos in peticiones
            ]

            resultados = [
                futuro.result(timeout=30)
                for futuro in futuros
            ]

        self.assertEqual(resultados, [302] * len(peticiones))

    def test_dos_cobros_simultaneos_generan_un_solo_pago(self):
        self.ejecutar_simultaneamente(
            [
                (
                    self.bibliotecario1,
                    self.url_pago,
                    {"metodo": "EFECTIVO"},
                ),
                (
                    self.bibliotecario2,
                    self.url_pago,
                    {"metodo": "TARJETA"},
                ),
            ]
        )

        self.multa.refresh_from_db()

        self.assertEqual(self.multa.estado, "PAGADA")
        self.assertEqual(
            Pago.objects.filter(multa=self.multa).count(),
            1,
        )

        pago = Pago.objects.get(multa=self.multa)

        self.assertEqual(pago.monto, Decimal("30.00"))
        self.assertIn(
            pago.registrado_por_id,
            [self.bibliotecario1.pk, self.bibliotecario2.pk],
        )
        self.assertIsNone(self.multa.condonada_por_id)

    def test_pago_y_condonacion_simultaneos_no_se_mezclan(self):
        motivo = "Condonación autorizada de prueba."

        self.ejecutar_simultaneamente(
            [
                (
                    self.bibliotecario1,
                    self.url_pago,
                    {"metodo": "EFECTIVO"},
                ),
                (
                    self.bibliotecario2,
                    self.url_condonar,
                    {"justificacion": motivo},
                ),
            ]
        )

        self.multa.refresh_from_db()

        self.assertIn(
            self.multa.estado,
            ["PAGADA", "CONDONADA"],
        )

        if self.multa.estado == "PAGADA":
            pago = Pago.objects.get(multa=self.multa)

            self.assertEqual(pago.monto, Decimal("30.00"))
            self.assertEqual(
                pago.registrado_por_id,
                self.bibliotecario1.pk,
            )
            self.assertIsNone(self.multa.condonada_por_id)
            self.assertFalse(
                self.multa.justificacion_condonacion
            )
        else:
            self.assertFalse(
                Pago.objects.filter(multa=self.multa).exists()
            )
            self.assertEqual(
                self.multa.condonada_por_id,
                self.bibliotecario2.pk,
            )
            self.assertEqual(
                self.multa.justificacion_condonacion,
                motivo,
            )