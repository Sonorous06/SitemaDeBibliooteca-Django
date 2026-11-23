import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
try:
    django.setup()
except Exception:
    pass

from cuentas.models import Usuario, Profesor, Estudiante, Departamento, Carrera

# 1. Crear / obtener Departamento y Carrera base
depto, _ = Departamento.objects.get_or_create(nombre="Sistemas y Computación")
carrera, _ = Carrera.objects.get_or_create(clave="ISW", defaults={"nombre": "Ingeniería en Software"})

# 2. Crear Profesor: Nahomi
u_nahomi, creado_n = Usuario.objects.get_or_create(
    username="nahomi",
    defaults={
        "first_name": "Nahomi",
        "last_name": "Profesor",
        "email": "nahomi@anahuac.com",
        "tipo_usuario": "PROFESOR"
    }
)
if creado_n:
    u_nahomi.set_password("nahomi123")
    u_nahomi.save()

Profesor.objects.get_or_create(
    usuario=u_nahomi,
    defaults={
        "num_empleado": "EMP-2001",
        "departamento": depto
    }
)

# 3. Crear Alumna 1: Denisse
u_denisse, creado_d = Usuario.objects.get_or_create(
    username="denisse",
    defaults={
        "first_name": "Denisse",
        "last_name": "Estudiante",
        "email": "denisse@anahuac.com",
        "tipo_usuario": "ESTUDIANTE"
    }
)
if creado_d:
    u_denisse.set_password("denisse123")
    u_denisse.save()

Estudiante.objects.get_or_create(
    usuario=u_denisse,
    defaults={
        "matricula": "MAT-3001",
        "carrera": carrera,
        "semestre": 5
    }
)

# 4. Crear Alumno 2: Francisco
u_francisco, creado_f = Usuario.objects.get_or_create(
    username="francisco",
    defaults={
        "first_name": "Francisco",
        "last_name": "Estudiante",
        "email": "francisco@anahuac.com",
        "tipo_usuario": "ESTUDIANTE"
    }
)
if creado_f:
    u_francisco.set_password("francisco123")
    u_francisco.save()

Estudiante.objects.get_or_create(
    usuario=u_francisco,
    defaults={
        "matricula": "MAT-3002",
        "carrera": carrera,
        "semestre": 5
    }
)

print("¡Usuarios (Nahomi, Denisse, Francisco) creados exitosamente!")
