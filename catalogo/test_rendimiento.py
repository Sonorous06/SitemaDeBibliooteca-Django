from time import perf_counter

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from .models import (
    Autor,
    Categoria,
    Editorial,
    Ejemplar,
    Libro,
    LibroAutor,
)


@override_settings(DEBUG=False)
class RendimientoCatalogoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(
            username="lector_rendimiento",
            tipo_usuario="ESTUDIANTE",
        )

        cls.categoria = Categoria.objects.create(
            nombre="Categoría de carga",
        )
        editorial = Editorial.objects.create(
            nombre="Editorial de carga",
        )
        autor = Autor.objects.create(
            nombre="AutorCarga",
            apellidos="Prueba",
        )

        Libro.objects.bulk_create(
            [
                Libro(
                    isbn=f"978{numero:010d}",
                    titulo=f"Libro de prueba {numero:05d}",
                    categoria=cls.categoria,
                    editorial=editorial,
                    activo=True,
                )
                for numero in range(10000)
            ],
            batch_size=500,
        )

        # Consultamos los IDs para funcionar también en MySQL.
        libros_ids = list(
            Libro.objects.order_by("pk").values_list(
                "pk", flat=True
            )
        )

        LibroAutor.objects.bulk_create(
            [
                LibroAutor(
                    libro_id=libro_id,
                    autor=autor,
                    orden=1,
                )
                for libro_id in libros_ids
            ],
            batch_size=500,
        )

        Ejemplar.objects.bulk_create(
            [
                Ejemplar(
                    libro_id=libro_id,
                    codigo_inventario=f"CARGA-{numero:05d}",
                    estado="DISPONIBLE",
                )
                for numero, libro_id in enumerate(libros_ids)
            ],
            batch_size=500,
        )

    def setUp(self):
        self.client.force_login(self.usuario)
        self.url = reverse("catalogo")

    def test_paginacion_y_filtros(self):
        primera = self.client.get(self.url)
        self.assertEqual(primera.status_code, 200)

        pagina = primera.context["pagina"]
        self.assertEqual(pagina.paginator.count, 10000)
        self.assertEqual(len(pagina.object_list), 12)

        ultima = self.client.get(
            self.url,
            {"pagina": pagina.paginator.num_pages},
        )
        self.assertEqual(ultima.status_code, 200)
        self.assertEqual(
            len(ultima.context["pagina"].object_list), 4
        )

        filtrada = self.client.get(
            self.url,
            {
                "q": "Libro de prueba",
                "categoria": self.categoria.pk,
                "pagina": 2,
            },
        )
        self.assertEqual(filtrada.status_code, 200)
        self.assertEqual(filtrada.context["pagina"].number, 2)
        self.assertEqual(
            filtrada.context["pagina"].paginator.count, 10000
        )
        self.assertIn(
            "q=Libro+de+prueba",
            filtrada.context["filtros_url"],
        )
        self.assertIn(
            f"categoria={self.categoria.pk}",
            filtrada.context["filtros_url"],
        )

    def test_busquedas_en_menos_de_dos_segundos(self):
        casos = [
            ("Título", {"q": "Libro de prueba"}, 10000),
            ("Autor", {"q": "AutorCarga"}, 10000),
            ("ISBN", {"q": "9780000000000"}, 1),
            (
                "Categoría",
                {"categoria": self.categoria.pk},
                10000,
            ),
            ("Sin resultados", {"q": "NoExisteXYZ"}, 0),
        ]

        for nombre, parametros, cantidad in casos:
            with self.subTest(busqueda=nombre):
                tiempos = []

                for _ in range(3):
                    inicio = perf_counter()
                    respuesta = self.client.get(
                        self.url, parametros
                    )
                    # Incluimos la generación del HTML en el tiempo.
                    contenido = respuesta.content
                    tiempos.append(perf_counter() - inicio)

                    self.assertEqual(respuesta.status_code, 200)
                    self.assertTrue(contenido)
                    self.assertEqual(
                        respuesta.context["pagina"].paginator.count,
                        cantidad,
                    )

                peor_tiempo = max(tiempos)
                print(
                    f"\n{nombre}: máximo de 3 consultas "
                    f"= {peor_tiempo:.3f} segundos",
                    flush=True,
                )
                self.assertLess(
                    peor_tiempo,
                    2.0,
                    f"La búsqueda por {nombre} superó 2 segundos.",
                )

    def test_consultas_no_aumentan_por_cada_tarjeta(self):
        with CaptureQueriesContext(connection) as consulta_uno:
            respuesta = self.client.get(
                self.url, {"q": "9780000000000"}
            )
            self.assertEqual(respuesta.status_code, 200)

        with CaptureQueriesContext(connection) as consulta_doce:
            respuesta = self.client.get(self.url)
            self.assertEqual(respuesta.status_code, 200)

        self.assertLessEqual(
            len(consulta_doce),
            len(consulta_uno) + 1,
            "Mostrar más tarjetas genera consultas adicionales "
            "por libro. Revisa las relaciones del catálogo.",
        )