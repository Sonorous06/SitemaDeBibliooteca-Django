import os
import sys

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import transaction

from cuentas.models import (
    Carrera,
    Departamento,
    Estudiante,
    Profesor,
    Usuario,
)


PASSWORD_DEMO = "BibliotecaDemo2026!"


# Usuario, nombre y apellidos.
ESTUDIANTES = [
    ("denisse", "Denisse", "Mireles"),
    ("francisco", "Francisco", "López"),
    ("ana_torres", "Ana", "Torres"),
    ("luis_garcia", "Luis", "García"),
    ("sofia_hernandez", "Sofía", "Hernández"),
    ("diego_ramirez", "Diego", "Ramírez"),
    ("valeria_sanchez", "Valeria", "Sánchez"),
    ("carlos_martinez", "Carlos", "Martínez"),
    ("mariana_flores", "Mariana", "Flores"),
    ("andres_gomez", "Andrés", "Gómez"),
    ("daniela_vargas", "Daniela", "Vargas"),
    ("alejandro_castro", "Alejandro", "Castro"),
    ("camila_ortiz", "Camila", "Ortiz"),
    ("mateo_ruiz", "Mateo", "Ruiz"),
    ("paula_navarro", "Paula", "Navarro"),
    ("santiago_mendoza", "Santiago", "Mendoza"),
    ("regina_silva", "Regina", "Silva"),
    ("emiliano_rojas", "Emiliano", "Rojas"),
    ("lucia_morales", "Lucía", "Morales"),
    ("sebastian_reyes", "Sebastián", "Reyes"),
]

PROFESORES = [
    ("carolina_romero", "Carolina", "Romero"),
    ("ricardo_vega", "Ricardo", "Vega"),
    ("patricia_salazar", "Patricia", "Salazar"),
    ("fernando_cruz", "Fernando", "Cruz"),
    ("monica_herrera", "Mónica", "Herrera"),
]

BIBLIOTECARIOS = [
    ("laura_medina", "Laura", "Medina"),
    ("roberto_santos", "Roberto", "Santos"),
]


def obtener_o_crear_usuario(datos, tipo_usuario):
    """Conserva los datos y la contraseña de una cuenta existente."""
    username, nombre, apellidos = datos

    usuario = Usuario.objects.filter(
        username__iexact=username,
    ).first()

    if usuario is not None:
        if usuario.tipo_usuario != tipo_usuario:
            raise ValueError(
                f"La cuenta '{username}' ya existe con el rol "
                f"{usuario.tipo_usuario}. No se modificó."
            )

        return usuario, False

    usuario = Usuario.objects.create_user(
        username=username,
        first_name=nombre,
        last_name=apellidos,
        email=f"{username}@biblioteca.example.com",
        password=PASSWORD_DEMO,
        tipo_usuario=tipo_usuario,
        is_active=True,
        is_staff=False,
        is_superuser=False,
    )

    return usuario, True


@transaction.atomic
def cargar_usuarios():
    """Prepara 20 estudiantes, 5 profesores y 2 bibliotecarios."""
    departamento, _ = Departamento.objects.get_or_create(
        nombre="Sistemas y Computación",
    )

    carrera, _ = Carrera.objects.get_or_create(
        clave="ISW",
        defaults={"nombre": "Ingeniería en Software"},
    )

    creados = {
        "ESTUDIANTE": 0,
        "PROFESOR": 0,
        "BIBLIOTECARIO": 0,
    }

    print("Preparando estudiantes...\n")

    for numero, datos in enumerate(ESTUDIANTES, start=1):
        usuario, nuevo = obtener_o_crear_usuario(
            datos,
            "ESTUDIANTE",
        )

        # Conservamos las matrículas del script original.
        if usuario.username.lower() == "denisse":
            matricula = "MAT-3001"
        elif usuario.username.lower() == "francisco":
            matricula = "MAT-3002"
        else:
            matricula = f"DEMO-E{numero:03d}"

        Estudiante.objects.get_or_create(
            usuario=usuario,
            defaults={
                "matricula": matricula,
                "carrera": carrera,
                "semestre": (
                    5 if numero <= 2 else ((numero - 1) % 12) + 1
                ),
            },
        )

        creados["ESTUDIANTE"] += int(nuevo)
        estado = "creada" if nuevo else "existente"
        print(f"  {usuario.username}: cuenta {estado}")

    print("\nPreparando profesores...\n")

    for numero, datos in enumerate(PROFESORES, start=1):
        usuario, nuevo = obtener_o_crear_usuario(
            datos,
            "PROFESOR",
        )

        Profesor.objects.get_or_create(
            usuario=usuario,
            defaults={
                "num_empleado": f"DEMO-P{numero:03d}",
                "departamento": departamento,
            },
        )

        creados["PROFESOR"] += int(nuevo)
        estado = "creada" if nuevo else "existente"
        print(f"  {usuario.username}: cuenta {estado}")

    print("\nPreparando bibliotecarios...\n")

    for datos in BIBLIOTECARIOS:
        usuario, nuevo = obtener_o_crear_usuario(
            datos,
            "BIBLIOTECARIO",
        )

        creados["BIBLIOTECARIO"] += int(nuevo)
        estado = "creada" if nuevo else "existente"
        print(f"  {usuario.username}: cuenta {estado}")

    return creados


if __name__ == "__main__":
    try:
        resultado = cargar_usuarios()

        print("\nCarga completada correctamente.")
        print(
            "Estudiantes nuevos: "
            f"{resultado['ESTUDIANTE']}"
        )
        print(
            "Profesores nuevos: "
            f"{resultado['PROFESOR']}"
        )
        print(
            "Bibliotecarios nuevos: "
            f"{resultado['BIBLIOTECARIO']}"
        )

        print("\nTotales actuales de usuarios por rol:")

        for rol in ["ESTUDIANTE", "PROFESOR", "BIBLIOTECARIO"]:
            cantidad = Usuario.objects.filter(
                tipo_usuario=rol,
            ).count()

            print(f"  {rol}: {cantidad}")

        print(
            "\nLas contraseñas de las cuentas existentes "
            "se conservaron."
        )

    except Exception as error:
        print(
            f"\nCarga cancelada y revertida: {error}",
            file=sys.stderr,
        )
        sys.exit(1)