import os
import sys
from decimal import Decimal

import django

# Preparar Django para ejecutar este archivo directamente.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import transaction
from django.db.models import Q

from catalogo.models import (
    Autor,
    Categoria,
    Editorial,
    Ejemplar,
    Libro,
    LibroAutor,
)


CATEGORIAS = {
    "PRG": (
        "Programación y Software",
        "Desarrollo de software, ingeniería, patrones y lenguajes.",
        "Estante A1",
    ),
    "MAT": (
        "Matemáticas y Estadística",
        "Álgebra, cálculo, estadística y matemáticas aplicadas.",
        "Estante B1",
    ),
    "FIS": (
        "Ciencias y Física",
        "Física, astronomía, biología y química.",
        "Estante C1",
    ),
    "LIT": (
        "Literatura Universal",
        "Novelas, narrativa y obras literarias.",
        "Estante D1",
    ),
    "HIS": (
        "Historia y Ciencias Sociales",
        "Historia, antropología, sociología y economía.",
        "Estante E1",
    ),
    "PSI": (
        "Psicología y Filosofía",
        "Conducta humana, pensamiento y filosofía.",
        "Estante F1",
    ),
}


PAISES_EDITORIALES = {
    "Prentice Hall": "EE.UU.",
    "Addison-Wesley": "EE.UU.",
    "McGraw-Hill": "México",
    "Editorial Sudamericana": "Argentina",
    "Alfaguara": "España",
    "O'Reilly Media": "EE.UU.",
    "Penguin Random House": "Reino Unido",
    "Editorial Crítica": "España",
}


# Los 13 libros que ya tenía el script.
# Los registros existentes se conservan sin actualizar sus datos.
LIBROS_BASE = [
    {
        "isbn": "9780132350884",
        "titulo": (
            "Clean Code: A Handbook of Agile Software Craftsmanship"
        ),
        "categoria": "PRG",
        "editorial": "Prentice Hall",
        "anio": 2008,
        "costo": "450.00",
        "nombre": "Robert C.",
        "apellidos": "Martin",
        "inventario": "INV-PRG-01",
        "idioma": "Inglés",
    },
    {
        "isbn": "9780201633610",
        "titulo": (
            "Design Patterns: Elements of Reusable "
            "Object-Oriented Software"
        ),
        "categoria": "PRG",
        "editorial": "Addison-Wesley",
        "anio": 1994,
        "costo": "520.00",
        "nombre": "Erich",
        "apellidos": "Gamma",
        "inventario": "INV-PRG-02",
        "idioma": "Inglés",
    },
    {
        "isbn": "9781491946008",
        "titulo": (
            "Fluent Python: Clear, Concise, and Effective Programming"
        ),
        "categoria": "PRG",
        "editorial": "O'Reilly Media",
        "anio": 2015,
        "costo": "480.00",
        "nombre": "Luciano",
        "apellidos": "Ramalho",
        "inventario": "INV-PRG-03",
        "idioma": "Inglés",
    },
    {
        "isbn": "9786073231589",
        "titulo": "Cálculo de una variable",
        "categoria": "MAT",
        "editorial": "Addison-Wesley",
        "anio": 2015,
        "costo": "620.00",
        "nombre": "George B.",
        "apellidos": "Thomas",
        "inventario": "INV-MAT-01",
        "idioma": "Español",
    },
    {
        "isbn": "9786073213981",
        "titulo": "Álgebra lineal y sus aplicaciones",
        "categoria": "MAT",
        "editorial": "Prentice Hall",
        "anio": 2012,
        "costo": "540.00",
        "nombre": "David C.",
        "apellidos": "Lay",
        "inventario": "INV-MAT-02",
        "idioma": "Español",
    },
    {
        "isbn": "9786073221900",
        "titulo": "Física Universitaria con Física Moderna Vol. 1",
        "categoria": "FIS",
        "editorial": "Addison-Wesley",
        "anio": 2013,
        "costo": "750.00",
        "nombre": "Hugh D.",
        "apellidos": "Young",
        "inventario": "INV-FIS-01",
        "idioma": "Español",
    },
    {
        "isbn": "9780553380163",
        "titulo": (
            "Historia del tiempo: Del Big Bang a los agujeros negros"
        ),
        "categoria": "FIS",
        "editorial": "Penguin Random House",
        "anio": 1988,
        "costo": "320.00",
        "nombre": "Stephen",
        "apellidos": "Hawking",
        "inventario": "INV-FIS-02",
        "idioma": "Español",
    },
    {
        "isbn": "9780307474728",
        "titulo": "Cien años de soledad",
        "categoria": "LIT",
        "editorial": "Editorial Sudamericana",
        "anio": 1967,
        "costo": "350.00",
        "nombre": "Gabriel",
        "apellidos": "García Márquez",
        "inventario": "INV-LIT-01",
        "idioma": "Español",
    },
    {
        "isbn": "9788424116033",
        "titulo": "Don Quijote de la Mancha",
        "categoria": "LIT",
        "editorial": "Alfaguara",
        "anio": 1605,
        "costo": "400.00",
        "nombre": "Miguel de",
        "apellidos": "Cervantes",
        "inventario": "INV-LIT-02",
        "idioma": "Español",
    },
    {
        "isbn": "9780451524935",
        "titulo": "1984",
        "categoria": "LIT",
        "editorial": "Alfaguara",
        "anio": 1949,
        "costo": "280.00",
        "nombre": "George",
        "apellidos": "Orwell",
        "inventario": "INV-LIT-03",
        "idioma": "Español",
    },
    {
        "isbn": "9788420664088",
        "titulo": "Crimen y castigo",
        "categoria": "LIT",
        "editorial": "Editorial Crítica",
        "anio": 1866,
        "costo": "390.00",
        "nombre": "Fiódor",
        "apellidos": "Dostoyevski",
        "inventario": "INV-LIT-04",
        "idioma": "Español",
    },
    {
        "isbn": "9780062316097",
        "titulo": "Sapiens: De animales a dioses",
        "categoria": "HIS",
        "editorial": "Penguin Random House",
        "anio": 2014,
        "costo": "420.00",
        "nombre": "Yuval Noah",
        "apellidos": "Harari",
        "inventario": "INV-HIS-01",
        "idioma": "Español",
    },
    {
        "isbn": "9780374533557",
        "titulo": "Pensar rápido, pensar despacio",
        "categoria": "PSI",
        "editorial": "Penguin Random House",
        "anio": 2011,
        "costo": "410.00",
        "nombre": "Daniel",
        "apellidos": "Kahneman",
        "inventario": "INV-PSI-01",
        "idioma": "Español",
    },
]


# Títulos adicionales para completar la demostración.
# Cada línea contiene: título | nombre | apellidos.
# En obras con varios autores se registra un autor principal.
LIBROS_DEMO = {
    "PRG": """
The Pragmatic Programmer|Andrew|Hunt
Introduction to Algorithms|Thomas H.|Cormen
Computer Networks|Andrew S.|Tanenbaum
Operating System Concepts|Abraham|Silberschatz
Artificial Intelligence: A Modern Approach|Stuart|Russell
Head First Design Patterns|Eric|Freeman
Computer Organization and Architecture|William|Stallings
Database System Concepts|Abraham|Silberschatz
Introduction to the Theory of Computation|Michael|Sipser
Structure and Interpretation of Computer Programs|Harold|Abelson
Refactoring|Martin|Fowler
The Mythical Man-Month|Frederick P.|Brooks
Algorithms|Robert|Sedgewick
Deep Learning|Ian|Goodfellow
Computer Systems: A Programmer's Perspective|Randal E.|Bryant
""",
    "MAT": """
Cálculo|James|Stewart
Álgebra|Aurelio|Baldor
Geometría y trigonometría|Aurelio|Baldor
Ecuaciones diferenciales con aplicaciones de modelado|Dennis G.|Zill
Álgebra lineal|Stanley I.|Grossman
Matemáticas discretas y sus aplicaciones|Kenneth H.|Rosen
Probabilidad y estadística para ingeniería y ciencias|Ronald E.|Walpole
Estadística para administración y economía|David R.|Anderson
Introducción a la probabilidad|Sheldon|Ross
Análisis numérico|Richard L.|Burden
Métodos numéricos para ingenieros|Steven C.|Chapra
Introducción al álgebra lineal|Gilbert|Strang
Cómo plantear y resolver problemas|George|Pólya
El hombre que calculaba|Malba|Tahan
El diablo de los números|Hans Magnus|Enzensberger
""",
    "FIS": """
Cosmos|Carl|Sagan
El mundo y sus demonios|Carl|Sagan
Un punto azul pálido|Carl|Sagan
Breves respuestas a las grandes preguntas|Stephen|Hawking
El universo en una cáscara de nuez|Stephen|Hawking
Seis piezas fáciles|Richard P.|Feynman
El carácter de la ley física|Richard P.|Feynman
Sobre la teoría de la relatividad especial y general|Albert|Einstein
¿Qué es la vida?|Erwin|Schrödinger
El gen egoísta|Richard|Dawkins
El origen de las especies|Charles|Darwin
Una breve historia de casi todo|Bill|Bryson
La estructura de las revoluciones científicas|Thomas S.|Kuhn
Química|Raymond|Chang
Química: la ciencia central|Theodore L.|Brown
""",
    "LIT": """
Orgullo y prejuicio|Jane|Austen
Sentido y sensibilidad|Jane|Austen
Emma|Jane|Austen
Jane Eyre|Charlotte|Brontë
Cumbres borrascosas|Emily|Brontë
Frankenstein|Mary|Shelley
Drácula|Bram|Stoker
El retrato de Dorian Gray|Oscar|Wilde
Los miserables|Victor|Hugo
El conde de Montecristo|Alexandre|Dumas
Los tres mosqueteros|Alexandre|Dumas
La vuelta al mundo en ochenta días|Jules|Verne
Viaje al centro de la Tierra|Jules|Verne
Veinte mil leguas de viaje submarino|Jules|Verne
La metamorfosis|Franz|Kafka
""",
    "HIS": """
Homo Deus|Yuval Noah|Harari
21 lecciones para el siglo XXI|Yuval Noah|Harari
El hombre en busca de sentido|Viktor E.|Frankl
Las venas abiertas de América Latina|Eduardo|Galeano
Los hijos de los días|Eduardo|Galeano
El laberinto de la soledad|Octavio|Paz
Visión de los vencidos|Miguel|León-Portilla
Historia mínima de México|Daniel|Cosío Villegas
La riqueza de las naciones|Adam|Smith
El capital|Karl|Marx
Economía y sociedad|Max|Weber
La ética protestante y el espíritu del capitalismo|Max|Weber
La sociedad del cansancio|Byung-Chul|Han
Modernidad líquida|Zygmunt|Bauman
La imaginación sociológica|C. Wright|Mills
""",
    "PSI": """
La República|Platón|
Apología de Sócrates|Platón|
Ética a Nicómaco|Aristóteles|
Política|Aristóteles|
Meditaciones|Marco|Aurelio
Discurso del método|René|Descartes
Meditaciones metafísicas|René|Descartes
Crítica de la razón pura|Immanuel|Kant
Fundamentación de la metafísica de las costumbres|Immanuel|Kant
Así habló Zaratustra|Friedrich|Nietzsche
Más allá del bien y del mal|Friedrich|Nietzsche
El contrato social|Jean-Jacques|Rousseau
El arte de amar|Erich|Fromm
El miedo a la libertad|Erich|Fromm
La interpretación de los sueños|Sigmund|Freud
""",
}


def crear_libro_con_ejemplar(datos):
    """Crea un título nuevo y su ejemplar sin actualizar los existentes."""
    existe = Libro.objects.filter(
        Q(isbn=datos["isbn"])
        | Q(titulo__iexact=datos["titulo"])
    ).exists()

    if existe:
        return False

    if Ejemplar.objects.filter(
        codigo_inventario=datos["inventario"],
    ).exists():
        raise ValueError(
            "El código de inventario "
            f"{datos['inventario']} ya pertenece a otro registro."
        )

    nombre_categoria, descripcion, ubicacion = CATEGORIAS[
        datos["categoria"]
    ]

    categoria, _ = Categoria.objects.get_or_create(
        nombre=nombre_categoria,
        defaults={"descripcion": descripcion},
    )

    editorial, _ = Editorial.objects.get_or_create(
        nombre=datos["editorial"],
        defaults={
            "pais": PAISES_EDITORIALES.get(
                datos["editorial"], ""
            ),
        },
    )

    autor, _ = Autor.objects.get_or_create(
        nombre=datos["nombre"],
        apellidos=datos["apellidos"],
    )

    libro = Libro.objects.create(
        isbn=datos["isbn"],
        titulo=datos["titulo"],
        categoria=categoria,
        editorial=editorial,
        anio_publicacion=datos.get("anio"),
        idioma=datos.get("idioma", "Español"),
        edicion=datos.get("edicion", ""),
        costo_reposicion=Decimal(datos["costo"]),
        activo=True,
    )

    LibroAutor.objects.create(
        libro=libro,
        autor=autor,
        orden=1,
    )

    Ejemplar.objects.create(
        libro=libro,
        codigo_inventario=datos["inventario"],
        ubicacion=ubicacion,
        estado="DISPONIBLE",
    )

    print(
        f"  + [{nombre_categoria}] "
        f"{libro.titulo} ({datos['inventario']})"
    )

    return True


@transaction.atomic
def cargar_catalogo(objetivo=100):
    """Completa el catálogo hasta alcanzar el total indicado."""
    total_inicial = Libro.objects.count()
    total_actual = total_inicial
    creados = 0

    print(f"Libros existentes: {total_inicial}")
    print(f"Objetivo de la demostración: {objetivo}\n")

    if total_actual >= objetivo:
        print("El catálogo ya alcanzó el objetivo.")
        return 0

    # Primero se consideran los libros del script original.
    for datos in LIBROS_BASE:
        if total_actual >= objetivo:
            break

        if crear_libro_con_ejemplar(datos):
            total_actual += 1
            creados += 1

    # Después se añaden los títulos de demostración necesarios.
    indice = 0

    for categoria, contenido in LIBROS_DEMO.items():
        for linea in contenido.strip().splitlines():
            indice += 1

            if total_actual >= objetivo:
                break

            titulo, nombre, apellidos = (
                campo.strip() for campo in linea.split("|")
            )

            # Si el título ya está registrado, se conserva.
            if Libro.objects.filter(
                titulo__iexact=titulo,
            ).exists():
                continue

            isbn_demo = f"DEMO{indice:09d}"

            if Libro.objects.filter(isbn=isbn_demo).exists():
                raise ValueError(
                    f"El identificador {isbn_demo} está ocupado "
                    "por un título diferente."
                )

            datos = {
                "isbn": isbn_demo,
                "titulo": titulo,
                "categoria": categoria,
                "editorial": "Edición de demostración",
                "anio": None,
                "costo": "300.00",
                "nombre": nombre,
                "apellidos": apellidos,
                "inventario": f"INV-DEMO-{indice:03d}",
                "idioma": (
                    "Inglés" if categoria == "PRG" else "Español"
                ),
                "edicion": "Demostración",
            }

            if crear_libro_con_ejemplar(datos):
                total_actual += 1
                creados += 1

        if total_actual >= objetivo:
            break

    if total_actual < objetivo:
        raise ValueError(
            f"La lista solo permitió alcanzar {total_actual} libros. "
            "Agrega más títulos diferentes antes de repetir la carga."
        )

    return creados


if __name__ == "__main__":
    try:
        print("Iniciando carga del catálogo...\n")

        nuevos = cargar_catalogo(objetivo=100)

        # Este resumen se imprime después de confirmar la transacción.
        print("\nCarga completada correctamente.")
        print(f"Libros nuevos: {nuevos}")
        print(f"Ejemplares nuevos: {nuevos}")
        print(f"Total de libros: {Libro.objects.count()}")
        print(
            "Total de libros activos: "
            f"{Libro.objects.filter(activo=True).count()}"
        )
        print(f"Total de ejemplares: {Ejemplar.objects.count()}")

    except Exception as error:
        print(
            f"\nCarga cancelada y revertida: {error}",
            file=sys.stderr,
        )
        sys.exit(1)