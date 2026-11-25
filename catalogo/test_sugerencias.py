from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .models import SugerenciaAdquisicion


class SeguridadSugerenciasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Usuario = get_user_model()

        cls.bibliotecario = Usuario.objects.create_user(
            username="bibliotecario_pruebas",
            tipo_usuario="BIBLIOTECARIO",
        )
        cls.profesor = Usuario.objects.create_user(
            username="profesor_pruebas",
            tipo_usuario="PROFESOR",
        )
        cls.lector = Usuario.objects.create_user(
            username="lector_pruebas",
            tipo_usuario="ESTUDIANTE",
        )

        cls.sugerencia = SugerenciaAdquisicion.objects.create(
            profesor=cls.profesor,
            titulo="Libro para la asignatura",
            autores="Autor de prueba",
            isbn="",
            justificacion="Material de apoyo para el curso.",
            estado="PENDIENTE",
        )

    def setUp(self):
        self.client.force_login(self.bibliotecario)

    def url_estado(self, estado):
        return reverse(
            "cambiar_estado_sugerencia",
            args=[self.sugerencia.pk, estado],
        )

    def comprobar_estado(self, esperado):
        self.sugerencia.refresh_from_db()
        self.assertEqual(self.sugerencia.estado, esperado)

    def test_get_no_modifica_la_sugerencia(self):
        respuesta = self.client.get(
            self.url_estado("APROBADA")
        )
        self.assertEqual(respuesta.status_code, 405)
        self.comprobar_estado("PENDIENTE")

    def test_bibliotecario_puede_aprobar_por_post(self):
        respuesta = self.client.post(
            self.url_estado("APROBADA")
        )
        self.assertEqual(respuesta.status_code, 302)
        self.comprobar_estado("APROBADA")

    def test_bibliotecario_puede_rechazar_por_post(self):
        respuesta = self.client.post(
            self.url_estado("RECHAZADA")
        )
        self.assertEqual(respuesta.status_code, 302)
        self.comprobar_estado("RECHAZADA")

    def test_lector_no_puede_procesar_sugerencias(self):
        self.client.force_login(self.lector)

        respuesta = self.client.post(
            self.url_estado("APROBADA")
        )
        self.assertEqual(respuesta.status_code, 302)
        self.comprobar_estado("PENDIENTE")

    def test_usuario_sin_sesion_no_puede_procesar(self):
        self.client.logout()

        respuesta = self.client.post(
            self.url_estado("APROBADA")
        )
        self.assertEqual(respuesta.status_code, 302)
        self.comprobar_estado("PENDIENTE")

    def test_estado_invalido_no_modifica_la_sugerencia(self):
        respuesta = self.client.post(
            self.url_estado("INVALIDO")
        )
        self.assertEqual(respuesta.status_code, 302)
        self.comprobar_estado("PENDIENTE")

    def test_segundo_intento_conserva_la_primera_decision(self):
        self.client.post(self.url_estado("APROBADA"))
        self.client.post(self.url_estado("RECHAZADA"))

        self.comprobar_estado("APROBADA")

    def test_post_sin_csrf_es_rechazado(self):
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.bibliotecario)

        respuesta = cliente.post(
            self.url_estado("APROBADA")
        )
        self.assertEqual(respuesta.status_code, 403)
        self.comprobar_estado("PENDIENTE")