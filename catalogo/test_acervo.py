from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from prestamos.models import Prestamo, Reserva
from .models import Autor, Categoria, Editorial, Ejemplar, Libro, LibroAutor


class GestionAcervoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        usuario = get_user_model()
        cls.bib = usuario.objects.create_user(
            username="bibliotecaria_acervo", tipo_usuario="BIBLIOTECARIO"
        )
        cls.lector = usuario.objects.create_user(
            username="lector_acervo", tipo_usuario="ESTUDIANTE"
        )
        cls.categoria = Categoria.objects.create(nombre="Ciencia")
        cls.editorial = Editorial.objects.create(nombre="Editorial prueba")
        cls.autor = Autor.objects.create(nombre="Ana", apellidos="Torres")
        cls.otro_autor = Autor.objects.create(nombre="Luis", apellidos="Vega")
        cls.libro = Libro.objects.create(
            isbn="9780000000001",
            titulo="Libro inicial",
            categoria=cls.categoria,
            editorial=cls.editorial,
            costo_reposicion=Decimal("300.00"),
        )
        LibroAutor.objects.create(libro=cls.libro, autor=cls.autor, orden=1)
        cls.ejemplar = Ejemplar.objects.create(
            libro=cls.libro, codigo_inventario="ACERVO-001"
        )

    def setUp(self):
        self.client.force_login(self.bib)

    def datos_libro(self, **cambios):
        datos = {
            "isbn": self.libro.isbn,
            "titulo": self.libro.titulo,
            "categoria": self.categoria.pk,
            "editorial": self.editorial.pk,
            "autores": [self.autor.pk],
            "idioma": "Español",
            "costo_reposicion": "300.00",
            "activo": "on",
        }
        datos.update(cambios)
        return datos

    def datos_ejemplar(self, **cambios):
        datos = {
            "codigo_inventario": "ACERVO-002",
            "ubicacion": "Estante 1",
            "estado": "DISPONIBLE",
        }
        datos.update(cambios)
        return datos

    def crear_prestamo(self, estado="ACTIVO"):
        self.ejemplar.estado = (
            "RESERVADO" if estado == "SOLICITADO" else "PRESTADO"
        )
        self.ejemplar.save(update_fields=["estado"])
        return Prestamo.objects.create(
            usuario=self.lector,
            ejemplar=self.ejemplar,
            estado=estado,
            fecha_vencimiento=timezone.localdate() + timedelta(days=7),
        )

    def test_bibliotecario_sin_staff_puede_crear_libro(self):
        self.assertFalse(self.bib.is_staff)
        respuesta = self.client.post(
            reverse("acervo_crear_libro"),
            self.datos_libro(
                isbn="9780000000002",
                titulo="Nuevo título",
                autores=[self.autor.pk, self.otro_autor.pk],
            ),
        )
        self.assertEqual(respuesta.status_code, 302)
        libro = Libro.objects.get(isbn="9780000000002")
        self.assertEqual(libro.autores.count(), 2)
        self.assertEqual(libro.ejemplares.count(), 0)

    def test_editar_libro_conserva_orden_de_autores(self):
        LibroAutor.objects.create(
            libro=self.libro, autor=self.otro_autor, orden=2
        )
        respuesta = self.client.post(
            reverse("acervo_editar_libro", args=[self.libro.pk]),
            self.datos_libro(
                titulo="Título corregido",
                autores=[self.otro_autor.pk, self.autor.pk],
            ),
        )
        self.assertEqual(respuesta.status_code, 302)
        self.libro.refresh_from_db()
        self.assertEqual(self.libro.titulo, "Título corregido")
        self.assertEqual(
            list(
                LibroAutor.objects.filter(libro=self.libro)
                .order_by("orden")
                .values_list("autor_id", flat=True)
            ),
            [self.autor.pk, self.otro_autor.pk],
        )

    def test_no_admite_costo_negativo(self):
        respuesta = self.client.post(
            reverse("acervo_editar_libro", args=[self.libro.pk]),
            self.datos_libro(costo_reposicion="-1.00"),
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("costo_reposicion", respuesta.context["form"].errors)
        self.libro.refresh_from_db()
        self.assertEqual(self.libro.costo_reposicion, Decimal("300.00"))

    def test_no_duplica_isbn(self):
        respuesta = self.client.post(
            reverse("acervo_crear_libro"),
            self.datos_libro(titulo="Otro título"),
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(Libro.objects.count(), 1)

    def test_no_inactiva_libro_con_prestamo(self):
        self.crear_prestamo()
        datos = self.datos_libro()
        datos.pop("activo")
        respuesta = self.client.post(
            reverse("acervo_editar_libro", args=[self.libro.pk]), datos
        )
        self.assertEqual(respuesta.status_code, 200)
        self.libro.refresh_from_db()
        self.assertTrue(self.libro.activo)

    def test_no_inactiva_libro_con_reserva_pendiente(self):
        Reserva.objects.create(
            usuario=self.lector, libro=self.libro, estado="PENDIENTE"
        )
        datos = self.datos_libro()
        datos.pop("activo")
        self.client.post(
            reverse("acervo_editar_libro", args=[self.libro.pk]), datos
        )
        self.libro.refresh_from_db()
        self.assertTrue(self.libro.activo)

    def test_inactivar_conserva_historial(self):
        prestamo = Prestamo.objects.create(
            usuario=self.lector, ejemplar=self.ejemplar, estado="DEVUELTO"
        )
        datos = self.datos_libro()
        datos.pop("activo")
        respuesta = self.client.post(
            reverse("acervo_editar_libro", args=[self.libro.pk]), datos
        )
        self.assertEqual(respuesta.status_code, 302)
        self.libro.refresh_from_db()
        self.assertFalse(self.libro.activo)
        self.assertTrue(Prestamo.objects.filter(pk=prestamo.pk).exists())
        self.assertTrue(Ejemplar.objects.filter(pk=self.ejemplar.pk).exists())

    def test_crea_ejemplar_disponible(self):
        respuesta = self.client.post(
            reverse("acervo_crear_ejemplar", args=[self.libro.pk]),
            self.datos_ejemplar(),
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(
            Ejemplar.objects.get(codigo_inventario="ACERVO-002").estado,
            "DISPONIBLE",
        )

    def test_no_duplica_inventario(self):
        respuesta = self.client.post(
            reverse("acervo_crear_ejemplar", args=[self.libro.pk]),
            self.datos_ejemplar(
                codigo_inventario=self.ejemplar.codigo_inventario
            ),
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(Ejemplar.objects.count(), 1)

    def test_no_asigna_prestado_o_reservado_manualmente(self):
        for estado in ["PRESTADO", "RESERVADO"]:
            with self.subTest(estado=estado):
                respuesta = self.client.post(
                    reverse("acervo_crear_ejemplar", args=[self.libro.pk]),
                    self.datos_ejemplar(estado=estado),
                )
                self.assertEqual(respuesta.status_code, 200)
                self.assertEqual(Ejemplar.objects.count(), 1)

    def test_no_da_de_baja_ejemplar_prestado(self):
        self.crear_prestamo()
        respuesta = self.client.post(
            reverse("acervo_editar_ejemplar", args=[self.ejemplar.pk]),
            self.datos_ejemplar(estado="BAJA"),
        )
        self.assertEqual(respuesta.status_code, 200)
        self.ejemplar.refresh_from_db()
        self.assertEqual(self.ejemplar.estado, "PRESTADO")

    def test_conserva_identidad_del_ejemplar(self):
        respuesta = self.client.post(
            reverse("acervo_editar_ejemplar", args=[self.ejemplar.pk]),
            self.datos_ejemplar(
                codigo_inventario="CAMBIADO", ubicacion="Estante 9"
            ),
        )
        self.assertEqual(respuesta.status_code, 302)
        self.ejemplar.refresh_from_db()
        self.assertEqual(self.ejemplar.codigo_inventario, "ACERVO-001")
        self.assertEqual(self.ejemplar.ubicacion, "Estante 9")

    def test_reparacion_a_disponible_atiende_reserva(self):
        self.ejemplar.estado = "EN_REPARACION"
        self.ejemplar.save(update_fields=["estado"])
        reserva = Reserva.objects.create(
            usuario=self.lector, libro=self.libro, estado="PENDIENTE"
        )
        respuesta = self.client.post(
            reverse("acervo_editar_ejemplar", args=[self.ejemplar.pk]),
            self.datos_ejemplar(),
        )
        self.assertEqual(respuesta.status_code, 302)
        reserva.refresh_from_db()
        self.ejemplar.refresh_from_db()
        self.assertEqual(reserva.estado, "DISPONIBLE")
        self.assertEqual(reserva.ejemplar_asignado_id, self.ejemplar.pk)
        self.assertIsNotNone(reserva.fecha_expiracion)
        self.assertEqual(self.ejemplar.estado, "RESERVADO")

    def test_nuevo_ejemplar_atiende_reserva(self):
        self.ejemplar.estado = "EN_REPARACION"
        self.ejemplar.save(update_fields=["estado"])
        reserva = Reserva.objects.create(
            usuario=self.lector, libro=self.libro, estado="PENDIENTE"
        )
        self.client.post(
            reverse("acervo_crear_ejemplar", args=[self.libro.pk]),
            self.datos_ejemplar(),
        )
        reserva.refresh_from_db()
        nuevo = Ejemplar.objects.get(codigo_inventario="ACERVO-002")
        self.assertEqual(reserva.ejemplar_asignado_id, nuevo.pk)
        self.assertEqual(nuevo.estado, "RESERVADO")

    def test_lector_no_puede_modificar_el_acervo(self):
        self.client.force_login(self.lector)
        acciones = [
            ("acervo_crear_libro", [], self.datos_libro(isbn="9780000000002")),
            (
                "acervo_editar_libro",
                [self.libro.pk],
                self.datos_libro(titulo="No autorizado"),
            ),
            ("acervo_crear_ejemplar", [self.libro.pk], self.datos_ejemplar()),
            (
                "acervo_editar_ejemplar",
                [self.ejemplar.pk],
                self.datos_ejemplar(estado="BAJA"),
            ),
            ("acervo_crear_auxiliar", ["autores"], {"nombre": "Intruso"}),
            (
                "acervo_eliminar_auxiliar",
                ["categorias", self.categoria.pk],
                {},
            ),
        ]
        for nombre, args, datos in acciones:
            with self.subTest(vista=nombre):
                self.assertEqual(
                    self.client.post(
                        reverse(nombre, args=args), datos
                    ).status_code,
                    302,
                )
        self.libro.refresh_from_db()
        self.ejemplar.refresh_from_db()
        self.assertEqual(self.libro.titulo, "Libro inicial")
        self.assertEqual(self.ejemplar.estado, "DISPONIBLE")
        self.assertEqual(Libro.objects.count(), 1)
        self.assertEqual(Ejemplar.objects.count(), 1)
        self.assertEqual(Autor.objects.count(), 2)
        self.assertTrue(
            Categoria.objects.filter(pk=self.categoria.pk).exists()
        )

    def test_sin_sesion_no_puede_entrar(self):
        self.client.logout()
        respuesta = self.client.get(reverse("acervo_lista"))
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn("login", respuesta.url)

    def test_csrf_protege_las_operaciones(self):
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.bib)
        for nombre, args in [
            ("acervo_crear_libro", []),
            ("acervo_crear_ejemplar", [self.libro.pk]),
            ("acervo_crear_auxiliar", ["autores"]),
            ("acervo_eliminar_auxiliar", ["categorias", self.categoria.pk]),
        ]:
            with self.subTest(vista=nombre):
                self.assertEqual(
                    cliente.post(reverse(nombre, args=args), {}).status_code,
                    403,
                )

    def test_formularios_get_no_modifican_datos(self):
        for nombre, args in [
            ("acervo_crear_libro", []),
            ("acervo_editar_libro", [self.libro.pk]),
            ("acervo_crear_ejemplar", [self.libro.pk]),
            ("acervo_editar_ejemplar", [self.ejemplar.pk]),
            ("acervo_crear_auxiliar", ["autores"]),
        ]:
            with self.subTest(vista=nombre):
                self.assertEqual(
                    self.client.get(reverse(nombre, args=args)).status_code,
                    200,
                )
        self.assertEqual(Libro.objects.count(), 1)
        self.assertEqual(Ejemplar.objects.count(), 1)

    def test_listado_incluye_inactivos_y_pagina(self):
        self.libro.activo = False
        self.libro.save(update_fields=["activo"])
        Libro.objects.bulk_create(
            [
                Libro(
                    isbn=f"978000000{n:04d}",
                    titulo=f"Libro {n:02d}",
                    categoria=self.categoria,
                    editorial=self.editorial,
                )
                for n in range(10, 25)
            ]
        )
        respuesta = self.client.get(reverse("acervo_lista"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context["pagina"].paginator.count, 16)
        self.assertEqual(len(respuesta.context["pagina"].object_list), 15)
        respuesta = self.client.get(
            reverse("acervo_lista"), {"estado": "inactivo"}
        )
        self.assertEqual(respuesta.context["pagina"].paginator.count, 1)

    def test_auxiliares_se_crean_y_editan(self):
        for tipo, modelo, datos in [
            ("autores", Autor, {"nombre": "Sócrates", "apellidos": ""}),
            ("categorias", Categoria, {"nombre": "Historia"}),
            (
                "editoriales",
                Editorial,
                {"nombre": "Otra editorial", "pais": "México"},
            ),
        ]:
            with self.subTest(tipo=tipo):
                respuesta = self.client.post(
                    reverse("acervo_crear_auxiliar", args=[tipo]), datos
                )
                self.assertEqual(respuesta.status_code, 302)
                registro = modelo.objects.get(nombre=datos["nombre"])
                datos["nombre"] += " editado"
                respuesta = self.client.post(
                    reverse(
                        "acervo_editar_auxiliar", args=[tipo, registro.pk]
                    ),
                    datos,
                )
                self.assertEqual(respuesta.status_code, 302)
                registro.refresh_from_db()
                self.assertEqual(registro.nombre, datos["nombre"])

    def test_auxiliar_asociado_no_se_elimina(self):
        for tipo, registro in [
            ("autores", self.autor),
            ("categorias", self.categoria),
            ("editoriales", self.editorial),
        ]:
            with self.subTest(tipo=tipo):
                respuesta = self.client.post(
                    reverse(
                        "acervo_eliminar_auxiliar", args=[tipo, registro.pk]
                    )
                )
                self.assertEqual(respuesta.status_code, 302)
                self.assertTrue(
                    type(registro).objects.filter(pk=registro.pk).exists()
                )

    def test_auxiliar_sin_uso_se_elimina_por_post(self):
        categoria = Categoria.objects.create(nombre="Sin uso")
        url = reverse(
            "acervo_eliminar_auxiliar", args=["categorias", categoria.pk]
        )
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertTrue(Categoria.objects.filter(pk=categoria.pk).exists())
        self.assertEqual(self.client.post(url).status_code, 302)
        self.assertFalse(Categoria.objects.filter(pk=categoria.pk).exists())

    def test_listados_auxiliares_renderizan(self):
        for tipo in ["autores", "categorias", "editoriales"]:
            with self.subTest(tipo=tipo):
                self.assertEqual(
                    self.client.get(
                        reverse("acervo_auxiliares", args=[tipo])
                    ).status_code,
                    200,
                )

    def test_seccion_desconocida_devuelve_404(self):
        self.assertEqual(
            self.client.get(
                reverse("acervo_auxiliares", args=["invalida"])
            ).status_code,
            404,
        )

    def test_catalogo_y_detalle_usan_pantallas_propias(self):
        respuesta = self.client.get(reverse("catalogo"))
        self.assertContains(respuesta, reverse("acervo_lista"))
        self.assertContains(
            respuesta, reverse("acervo_editar_libro", args=[self.libro.pk])
        )
        self.assertNotContains(respuesta, "/admin/catalogo/libro/")
        respuesta = self.client.get(
            reverse("detalle_libro", args=[self.libro.pk])
        )
        self.assertContains(
            respuesta, reverse("acervo_editar_libro", args=[self.libro.pk])
        )
        self.assertContains(
            respuesta, reverse("acervo_ejemplares", args=[self.libro.pk])
        )
        self.assertNotContains(respuesta, "admin/catalogo/libro/")

    def test_puede_crear_libro_con_portada(self):
        from io import BytesIO
        from pathlib import Path
        from tempfile import TemporaryDirectory

        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        imagen = BytesIO()
        Image.new("RGB", (8, 8), color="blue").save(imagen, format="PNG")
        archivo = SimpleUploadedFile(
            "portada.png", imagen.getvalue(), content_type="image/png"
        )
        with TemporaryDirectory() as carpeta:
            with self.settings(MEDIA_ROOT=carpeta):
                datos = self.datos_libro(
                    isbn="9780000000002", titulo="Con portada", portada=archivo
                )
                respuesta = self.client.post(
                    reverse("acervo_crear_libro"), datos
                )
                self.assertEqual(respuesta.status_code, 302)
                libro = Libro.objects.get(isbn="9780000000002")
                self.assertTrue(libro.portada.name)
                self.assertTrue(Path(libro.portada.path).is_file())
