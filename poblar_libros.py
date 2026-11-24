import os
import sys
import django

# Configurar entorno de Django para ejecución directa
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
try:
    django.setup()
except Exception:
    pass

from catalogo.models import Categoria, Editorial, Autor, Libro, LibroAutor, Ejemplar

def cargar_catalogo():
    print("Iniciando carga masiva de libros en el catálogo...\n")

    # 1. CATEGORÍAS
    categorias_def = [
        ("Programación y Software", "Desarrollo de software, ingeniería, patrones y lenguajes."),
        ("Matemáticas y Estadística", "Álgebra, cálculo, estadística y matemáticas aplicadas."),
        ("Ciencias y Física", "Física universitaria, mecánica, astronomía y química."),
        ("Literatura Universal", "Novelas clásicas, narrativa y obras literarias fundamentales."),
        ("Historia y Ciencias Sociales", "Historia mundial, antropología, sociología y economía."),
        ("Psicología y Filosofía", "Estudio de la mente, conducta humana y filosofía clásica.")
    ]

    cats = {}
    for nom, desc in categorias_def:
        cat, _ = Categoria.objects.get_or_create(nombre=nom, defaults={'descripcion': desc})
        cats[nom] = cat
        print(f"  ✓ Categoría: {nom}")

    # 2. EDITORIALES
    editoriales_def = [
        ("Prentice Hall", "EE.UU."),
        ("Addison-Wesley", "EE.UU."),
        ("McGraw-Hill", "México"),
        ("Editorial Sudamericana", "Argentina"),
        ("Alfaguara", "España"),
        ("O'Reilly Media", "EE.UU."),
        ("Penguin Random House", "Reino Unido"),
        ("Editorial Crítica", "España")
    ]

    eds = {}
    for nom, pais in editoriales_def:
        ed, _ = Editorial.objects.get_or_create(nombre=nom, defaults={'pais': pais})
        eds[nom] = ed
        print(f"  ✓ Editorial: {nom}")

    # 3. AUTORES
    autores_def = [
        ("Robert C.", "Martin", "Estadounidense"),
        ("Erich", "Gamma", "Suizo"),
        ("Luciano", "Ramalho", "Brasilero"),
        ("George B.", "Thomas", "Estadounidense"),
        ("David C.", "Lay", "Estadounidense"),
        ("Hugh D.", "Young", "Estadounidense"),
        ("Stephen", "Hawking", "Británico"),
        ("Gabriel", "García Márquez", "Colombiano"),
        ("Miguel de", "Cervantes", "Español"),
        ("George", "Orwell", "Británico"),
        ("Yuval Noah", "Harari", "Israelí"),
        ("Daniel", "Kahneman", "Israelí"),
        ("Fiódor", "Dostoyevski", "Ruso"),
    ]

    autores = {}
    for nom, ape, nac in autores_def:
        key = f"{nom} {ape}"
        aut, _ = Autor.objects.get_or_create(nombre=nom, apellidos=ape, defaults={'nacionalidad': nac})
        autores[key] = aut

    print("\n Insertando libros y ejemplares...")

    # 4. LIBROS CON SUS RESPECTIVAS CATEGORÍAS
    libros = [
        # Programación y Software
        {
            "isbn": "9780132350884", "titulo": "Clean Code: A Handbook of Agile Software Craftsmanship",
            "cat": cats["Programación y Software"], "ed": eds["Prentice Hall"], "anio": 2008, "costo": 450.00,
            "autor": autores["Robert C. Martin"], "inv": "INV-PRG-01", "ubicacion": "Estante A1"
        },
        {
            "isbn": "9780201633610", "titulo": "Design Patterns: Elements of Reusable Object-Oriented Software",
            "cat": cats["Programación y Software"], "ed": eds["Addison-Wesley"], "anio": 1994, "costo": 520.00,
            "autor": autores["Erich Gamma"], "inv": "INV-PRG-02", "ubicacion": "Estante A1"
        },
        {
            "isbn": "9781491946008", "titulo": "Fluent Python: Clear, Concise, and Effective Programming",
            "cat": cats["Programación y Software"], "ed": eds["O'Reilly Media"], "anio": 2015, "costo": 480.00,
            "autor": autores["Luciano Ramalho"], "inv": "INV-PRG-03", "ubicacion": "Estante A2"
        },

        # Matemáticas y Estadística
        {
            "isbn": "9786073231589", "titulo": "Cálculo de una variable",
            "cat": cats["Matemáticas y Estadística"], "ed": eds["Addison-Wesley"], "anio": 2015, "costo": 620.00,
            "autor": autores["George B. Thomas"], "inv": "INV-MAT-01", "ubicacion": "Estante B1"
        },
        {
            "isbn": "9786073213981", "titulo": "Álgebra lineal y sus aplicaciones",
            "cat": cats["Matemáticas y Estadística"], "ed": eds["Prentice Hall"], "anio": 2012, "costo": 540.00,
            "autor": autores["David C. Lay"], "inv": "INV-MAT-02", "ubicacion": "Estante B1"
        },

        # Ciencias y Física
        {
            "isbn": "9786073221900", "titulo": "Física Universitaria con Física Moderna Vol. 1",
            "cat": cats["Ciencias y Física"], "ed": eds["Addison-Wesley"], "anio": 2013, "costo": 750.00,
            "autor": autores["Hugh D. Young"], "inv": "INV-FIS-01", "ubicacion": "Estante C1"
        },
        {
            "isbn": "9780553380163", "titulo": "Historia del tiempo: Del Big Bang a los agujeros negros",
            "cat": cats["Ciencias y Física"], "ed": eds["Penguin Random House"], "anio": 1988, "costo": 320.00,
            "autor": autores["Stephen Hawking"], "inv": "INV-FIS-02", "ubicacion": "Estante C2"
        },

        # Literatura Universal
        {
            "isbn": "9780307474728", "titulo": "Cien años de soledad",
            "cat": cats["Literatura Universal"], "ed": eds["Editorial Sudamericana"], "anio": 1967, "costo": 350.00,
            "autor": autores["Gabriel García Márquez"], "inv": "INV-LIT-01", "ubicacion": "Estante D1"
        },
        {
            "isbn": "9788424116033", "titulo": "Don Quijote de la Mancha",
            "cat": cats["Literatura Universal"], "ed": eds["Alfaguara"], "anio": 1605, "costo": 400.00,
            "autor": autores["Miguel de Cervantes"], "inv": "INV-LIT-02", "ubicacion": "Estante D1"
        },
        {
            "isbn": "9780451524935", "titulo": "1984",
            "cat": cats["Literatura Universal"], "ed": eds["Alfaguara"], "anio": 1949, "costo": 280.00,
            "autor": autores["George Orwell"], "inv": "INV-LIT-03", "ubicacion": "Estante D2"
        },
        {
            "isbn": "9788420664088", "titulo": "Crimen y castigo",
            "cat": cats["Literatura Universal"], "ed": eds["Editorial Crítica"], "anio": 1866, "costo": 390.00,
            "autor": autores["Fiódor Dostoyevski"], "inv": "INV-LIT-04", "ubicacion": "Estante D2"
        },

        # Historia y Ciencias Sociales
        {
            "isbn": "9780062316097", "titulo": "Sapiens: De animales a dioses",
            "cat": cats["Historia y Ciencias Sociales"], "ed": eds["Penguin Random House"], "anio": 2014, "costo": 420.00,
            "autor": autores["Yuval Noah Harari"], "inv": "INV-HIS-01", "ubicacion": "Estante E1"
        },

        # Psicología y Filosofía
        {
            "isbn": "9780374533557", "titulo": "Pensar rápido, pensar despacio",
            "cat": cats["Psicología y Filosofía"], "ed": eds["Penguin Random House"], "anio": 2011, "costo": 410.00,
            "autor": autores["Daniel Kahneman"], "inv": "INV-PSI-01", "ubicacion": "Estante F1"
        }
    ]

    creados_count = 0
    for item in libros:
        libro, creado = Libro.objects.get_or_create(
            isbn=item["isbn"],
            defaults={
                "titulo": item["titulo"],
                "categoria": item["cat"],
                "editorial": item["ed"],
                "anio_publicacion": item["anio"],
                "costo_reposicion": item["costo"]
            }
        )
        
        # Asignar Autor si se creó el libro o no tiene autor aún
        if not LibroAutor.objects.filter(libro=libro, autor=item["autor"]).exists():
            LibroAutor.objects.create(libro=libro, autor=item["autor"], orden=1)
        
        # Crear al menos un ejemplar disponible
        if not Ejemplar.objects.filter(codigo_inventario=item["inv"]).exists():
            Ejemplar.objects.create(
                libro=libro,
                codigo_inventario=item["inv"],
                estado='DISPONIBLE',
                ubicacion=item["ubicacion"]
            )
        
        creados_count += 1
        print(f"  [{item['cat'].nombre}] {item['titulo']} ({item['inv']})")

    print(f"\n ¡Carga completada exitosamente! Se procesaron {creados_count} libros con sus ejemplares.")

if __name__ == "__main__":
    cargar_catalogo()