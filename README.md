# Sistema de Gestión de Biblioteca Escolar

Proyecto académico desarrollado con Python, Django y MySQL.
Se ejecuta localmente sin Docker.

Permite administrar lectores y catálogo, solicitar y entregar préstamos,
gestionar reservas, registrar devoluciones e incidencias y consultar
multas, pagos, notificaciones y reportes.

## Tecnologías

- Python 3.12 utilizado durante las pruebas.
- Django 5.2.
- MySQL con tablas transaccionales InnoDB.
- HTML, Tailwind CSS y JavaScript.
- Dependencias declaradas en `requirements.txt`.

La interfaz utiliza recursos externos para estilos y fuentes, por lo
que necesita conexión a Internet para cargarlos.

## Roles

| Rol | Funciones principales |
| --- | --- |
| Estudiante | Consultar catálogo, solicitar y cancelar préstamos pendientes, reservar, cancelar reservas, renovar y consultar su historial, multas y notificaciones. |
| Profesor | Funciones del lector y sugerencias de adquisición. |
| Bibliotecario | Gestionar lectores, importar CSV, administrar bloqueos, entregar y recibir ejemplares, registrar incidencias, pagos y condonaciones, configurar políticas y consultar reportes. |

El tipo `BIBLIOTECARIO` y los permisos de Django Admin son distintos.
Para acceder a `/admin/`, la cuenta también necesita estar activa,
tener `is_staff` y los permisos correspondientes.

## Funciones implementadas

### Cuentas

- Inicio y cierre de sesión.
- Recuperación de contraseña mediante enlace con token.
- Creación y edición de lectores con perfiles de estudiante o profesor.
- Importación CSV con validación de cuentas y perfiles.
- Reversión completa de la importación si alguna fila contiene errores.
- Bloqueo con motivo obligatorio y desbloqueo.
- Protección contra el bloqueo de la propia cuenta del bibliotecario.

### Catálogo

- Búsqueda por título, ISBN, autor y editorial.
- Filtro por categoría.
- Detalle del libro, autores ordenados y ejemplares paginados.
- Consulta de disponibilidad.
- Administración mediante Django Admin de libros, autores, editoriales,
  categorías y ejemplares.
- Protección en el administrador frente a cambios de estado incompatibles
  con préstamos y reservas vigentes.
- Conservación de libros y ejemplares mediante inactivación y baja.
- Sugerencias de adquisición de profesores y revisión del bibliotecario.

### Préstamos y reservas

- Solicitudes en línea mediante POST con protección CSRF.
- Cancelación de solicitudes pendientes de recoger.
- Entrega de solicitudes y préstamo directo en mostrador.
- Plazos y límites configurables según el tipo de lector.
- Renovación con comprobaciones de bloqueo, multas, vencimientos,
  reservas de otros lectores y límite de renovaciones.
- Registro del personal que entrega y recibe.
- Reservas y asignación por orden de llegada.
- Cancelación, recogida y expiración de reservas.
- Historial personal de préstamos y reservas.

### Multas

- Cálculo de multa por retraso al registrar la devolución.
- Registro de daños y pérdidas con multa por costo de reposición.
- Multa por retraso adicional cuando corresponde.
- Consulta personal de multas y total pendiente.
- Registro de liquidación en efectivo, tarjeta o transferencia.
- Folio de recibo y registro del bibliotecario que cobra.
- Condonación con justificación y registro del bibliotecario.
- Conservación del historial de pagos y condonaciones.

Los pagos son registros de cobros realizados en mostrador.
No hay una pasarela bancaria integrada.

### Notificaciones y tareas

- Avisos internos de vencimiento próximo, préstamo vencido y reserva
  disponible.
- Consulta de notificaciones propias y marcado como leídas.
- Comando `procesar_vencimientos`.
- Ejecución programada en Windows cada 15 minutos mediante scripts.

El comando marca vencimientos, expira solicitudes y reservas, reasigna
ejemplares y genera avisos. No genera una multa nueva cada día:
la multa por retraso se calcula al cerrar el préstamo mediante
devolución o incidencia.

### Reportes

- Préstamos entregados por período.
- Los 10 libros más prestados del período.
- Cobros por fecha de pago.
- Préstamos vencidos actualmente.
- Multas pendientes actuales y desglose por motivo.

Los vencimientos y saldos actuales no se limitan al período seleccionado
para entregas y cobros.

## Políticas iniciales

Las políticas pueden configurarse desde la pantalla del bibliotecario.

| Parámetro | Estudiantes | Profesores |
| --- | ---: | ---: |
| Días naturales de préstamo | 7 | 30 |
| Máximo de libros simultáneos | 3 | 10 |
| Renovaciones permitidas | 1 | 2 |
| Multa por día de retraso | $10.00 | $10.00 |
| Tope por retraso | $300.00 | $300.00 |
| Horas para recoger | 48 | 48 |

Las solicitudes pendientes de recoger cuentan para el límite de libros.
El vencimiento de una renovación se calcula desde el día en que se renueva.

Guardar políticas no modifica fechas ni multas ya registradas.
La tarifa vigente se consulta al calcular nuevas multas por retraso.

## Instalación local en Windows

### 1. Descargar el proyecto

En PowerShell:

```powershell
git clone https://github.com/Sonorous06/SitemaDeBibliooteca-Django.git
cd SitemaDeBibliooteca-Django
```

### 2. Preparar el entorno

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Los comandos utilizan directamente el Python del entorno virtual;
no es obligatorio activarlo.

### 3. Preparar MySQL

Iniciar MySQL y crear una base vacía desde Workbench para una instalación
nueva:

```sql
CREATE DATABASE biblioteca
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;
```

Si ya existe una base del proyecto, conservarla y utilizar su nombre.
No ejecutar scripts de creación de tablas sobre una base existente
sin revisar primero su contenido.

### 4. Configurar la conexión local

En `config/settings.py`, comprobar que existe `import os` y adaptar
el bloque `DATABASES` para utilizar variables de entorno:

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.environ.get("DB_NAME", "biblioteca"),
        "USER": os.environ.get("DB_USER", "root"),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "HOST": os.environ.get("DB_HOST", "127.0.0.1"),
        "PORT": os.environ.get("DB_PORT", "3306"),
        "OPTIONS": {
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}
```

Actualizar las opciones existentes sin duplicar claves.

En la terminal donde se ejecutará Django:

```powershell
$env:DB_NAME = "biblioteca"
$env:DB_USER = "root"
$env:DB_HOST = "127.0.0.1"
$env:DB_PORT = "3306"
$env:DB_PASSWORD = [System.Net.NetworkCredential]::new("", (Read-Host "Contraseña de MySQL" -AsSecureString)).Password
```

Usar el nombre y usuario reales de la base local.

Estas variables pertenecen a esa terminal. Si se abre otra terminal,
deben cargarse nuevamente.

La existencia de un archivo `.env` no garantiza que se cargue:
requiere una llamada explícita a `load_dotenv` o una configuración
equivalente.

No subir contraseñas personales al repositorio.

### 5. Aplicar las migraciones existentes

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py migrate --plan
.\.venv\Scripts\python.exe manage.py migrate
```

Para instalar se aplican las migraciones del repositorio; no es necesario
generar otras con `makemigrations`.

Comprobación de cambios de modelos pendientes:

```powershell
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
```

### 6. Crear una cuenta administrativa

```powershell
.\.venv\Scripts\python.exe manage.py createsuperuser --username bibliotecario
.\.venv\Scripts\python.exe manage.py shell
```

Dentro del shell:

```python
from django.contrib.auth import get_user_model

Usuario = get_user_model()
usuario = Usuario.objects.get(username="bibliotecario")
usuario.tipo_usuario = "BIBLIOTECARIO"
usuario.save(update_fields=["tipo_usuario"])

exit()
```

`createsuperuser` configura permisos administrativos; el paso adicional
establece el rol utilizado por las pantallas de la biblioteca.

### 7. Iniciar la aplicación

```powershell
.\.venv\Scripts\python.exe manage.py runserver
```

Abrir:

- Aplicación: http://127.0.0.1:8000/
- Administrador: http://127.0.0.1:8000/admin/

Detener el servidor con `Ctrl + C`.

## Preparación de datos

Una instalación nueva no incluye los datos de otro integrante.

Registrar carreras y departamentos antes de crear los perfiles de lectores.
Configurar las políticas desde el inicio del bibliotecario.

Para preparar el catálogo, registrar categorías, editoriales, autores,
libros y ejemplares con códigos de inventario únicos.

El repositorio incluye los scripts auxiliares `poblar_libros.py` y
`poblar_usuarios.py`. Revisar su contenido y las cuentas que crean antes
de utilizarlos. No sustituyen las migraciones ni crean una copia de los
datos locales de otro integrante.

## Importación de lectores

Disponible desde Usuarios → Importar CSV.

- Codificación UTF-8.
- Separador coma o punto y coma.
- Máximo 500 lectores y 1 MB.
- Se crean lectores nuevos; no se actualizan cuentas existentes.
- Las carreras y departamentos deben existir previamente.
- Si una fila es inválida, se revierte todo el lote.

Encabezado:

```csv
username,first_name,last_name,email,telefono,tipo_usuario,password,matricula,carrera,semestre,num_empleado,departamento
```

Para estudiantes se utiliza la clave de carrera.
Para profesores se utiliza el nombre exacto del departamento.

Dejar vacíos los campos del perfil que no corresponda.
Las contraseñas se almacenan mediante el sistema de hash de Django.

## Recuperación de contraseña en desarrollo

Para mostrar el enlace en la terminal, configurar en `settings.py`:

```python
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
```

Con este backend no se envía correo real. El enlace aparece en la terminal
del servidor. El envío por SMTP requiere configuración adicional.

## Vencimientos y avisos automáticos

Ejecución manual:

```powershell
.\.venv\Scripts\python.exe manage.py procesar_vencimientos
```

Para programarlo en Windows, seguir
[las instrucciones de tareas automáticas](docs/tareas_windows.md).

Las credenciales y registros se guardan fuera del repositorio.
Cada integrante configura la tarea en su propio equipo.

La configuración incluida requiere sesión de Windows iniciada,
computadora despierta y MySQL disponible. No requiere mantener abierto
`runserver`.

## Pruebas automatizadas

Ejecutar:

```powershell
.\.venv\Scripts\python.exe manage.py test prestamos multas --verbosity 2
```

El usuario de MySQL debe tener permisos para crear y eliminar la base
de datos de pruebas.

Se verificaron 60 pruebas en MySQL, sin pruebas omitidas:

- Solicitudes y restricciones de elegibilidad.
- Renovaciones y límites por rol.
- Permisos, privacidad y protección CSRF en los casos probados.
- Devoluciones y multas por retraso, daño y pérdida.
- Asignación y reasignación de reservas.
- Vencimientos y avisos sin duplicación.
- Pagos y condonaciones.
- Solicitudes simultáneas sobre un ejemplar y sobre el último cupo.
- Cobros simultáneos y competencia entre pago y condonación.

Las pruebas crean una base separada y eliminan esa base al terminar.
Estos resultados no equivalen a una auditoría completa de todos los
módulos, permisos o combinaciones de concurrencia.

## Rutas principales

| Ruta | Función |
| --- | --- |
| `/` | Inicio |
| `/admin/` | Administrador de Django |
| `/cuentas/usuarios/` | Gestión de usuarios |
| `/cuentas/usuarios/crear/` | Crear lector |
| `/cuentas/usuarios/importar/` | Importación CSV |
| `/cuentas/recuperar-password/` | Recuperación de contraseña |
| `/catalogo/` | Catálogo |
| `/catalogo/<id>` | Detalle del libro |
| `/catalogo/sugerencias/` | Revisión de sugerencias |
| `/prestamos/mis-prestamos/` | Historial de préstamos |
| `/prestamos/mis-reservas/` | Reservas propias |
| `/prestamos/solicitudes/` | Entregas pendientes |
| `/prestamos/reservas/por-entregar/` | Recogida de reservas |
| `/prestamos/mostrador/` | Préstamo directo |
| `/prestamos/devoluciones/` | Devoluciones e incidencias |
| `/prestamos/politicas/` | Políticas |
| `/prestamos/reportes/` | Reportes |
| `/multas/mis-multas/` | Multas propias |
| `/multas/pendientes/` | Gestión de multas |

Las rutas con identificadores representan registros concretos.
El menú muestra las opciones según el rol.

## Verificaciones pendientes de cierre

- Probar una instalación desde cero siguiendo este documento.
- Completar la revisión de permisos e integración de los demás módulos.
- Verificar paginación y rendimiento del catálogo y listas generales
  con el volumen de datos requerido.
- Ampliar las pruebas de concurrencia a los flujos todavía no cubiertos.
- Contrastar documentación, diagramas UML y evidencias con los requisitos
  de entrega del profesor.

## Colaboración

1. Actualizar `main` antes de comenzar.
2. Crear una rama para el cambio.
3. Ejecutar las comprobaciones correspondientes.
4. Revisar el diff y preparar únicamente los archivos necesarios.
5. Excluir credenciales, registros y configuraciones personales.
6. Crear un pull request hacia `main`.
7. Confirmar el merge antes de actualizar la copia local.

Git comparte código y migraciones, no los registros de MySQL.
Cada integrante aplica las migraciones en su propia base.