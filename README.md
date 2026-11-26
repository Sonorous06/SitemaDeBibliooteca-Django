# Sistema de Gestión de Biblioteca Escolar

Proyecto académico de Ingeniería de Software de la Universidad Anáhuac Norte,
desarrollado con Python, Django y MySQL. Se ejecuta localmente sin Docker.

**Estado: desarrollo finalizado para la entrega académica.**
La versión presentada integra las funciones descritas en este documento,
datos de demostración y una suite de 97 pruebas aprobadas en MySQL durante
la verificación de cierre. El resultado corresponde al entorno probado.

**Repositorio:** https://github.com/Sonorous06/SitemaDeBibliooteca-Django

## Equipo

- Francisco Javier Hernández Gómez.
- Denisse Mireles Salgado.
- Santiago Guillermo Lopez Chavez.
- Nahomi Massiel Romero Somilleda.

**Profesor:** Bárbaro Jorge Ferro Castro.

## Descripción del sistema

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

## Organización del proyecto

| Ubicación | Contenido |
| --- | --- |
| `cuentas/` | Usuarios, perfiles, autenticación, bloqueo, formularios de lectores e importación CSV. |
| `catalogo/` | Libros, autores, categorías, editoriales, ejemplares, sugerencias y gestión del acervo. |
| `prestamos/` | Solicitudes, entregas, devoluciones, renovaciones, reservas, incidencias, políticas y reportes. |
| `multas/` | Multas, pagos y condonaciones. |
| `notificaciones/` | Avisos internos y comando de vencimientos. |
| `config/` | Configuración general y rutas principales de Django. |
| `media/portadas/` | Archivos de las portadas cargadas desde el sistema. |
| `templates/` | Pantallas de Django; `inicio/` contiene las tarjetas del bibliotecario y `catalogo/acervo/` los formularios del acervo. |
| `scripts/` | Ejecución y configuración de la tarea automática en Windows. |
| `docs/` | Documentación; incluye `tareas_windows.md`. |
| `poblar_libros.py` y `poblar_usuarios.py` | Carga de datos de demostración. |

## Roles

| Rol | Funciones principales |
| --- | --- |
| Estudiante | Consultar catálogo, solicitar y cancelar préstamos pendientes, reservar, cancelar reservas, renovar y consultar su historial, multas y notificaciones. |
| Profesor | Funciones del lector y sugerencias de adquisición. |
| Bibliotecario | Gestionar acervo y lectores, importar CSV, administrar bloqueos, entregar y recibir ejemplares, registrar incidencias, pagos y condonaciones, revisar sugerencias, configurar políticas y consultar reportes. |

El tipo `BIBLIOTECARIO` y los permisos de Django Admin son distintos.
Para acceder a `/admin/`, la cuenta también necesita estar activa,
tener `is_staff` y los permisos correspondientes.

## Funciones implementadas

### Inicio

- Panel adaptado al rol del usuario.
- Cuatro tarjetas de operación diaria para el bibliotecario: entregar
  préstamos, préstamo en mostrador, registrar devolución y gestionar multas.
- Accesos de administración a reportes y políticas de préstamo.
- Resumen de solicitudes pendientes, préstamos que vencen hoy y vencidos.
- Consulta de próximos vencimientos y libros con poca disponibilidad.

### Cuentas

- Inicio y cierre de sesión.
- Recuperación de contraseña mediante enlace con token.
- Creación y edición de lectores con perfiles de estudiante o profesor.
- Importación CSV con validación de cuentas y perfiles.
- Reversión completa de la importación si alguna fila contiene errores.
- Bloqueo con motivo obligatorio y desbloqueo.
- Protección contra el bloqueo de la propia cuenta del bibliotecario.

### Catálogo y gestión del acervo

- Búsqueda por título, ISBN, autor, editorial y nombre de categoría.
- Filtro desplegable por categoría.
- Catálogo paginado en grupos de 12 libros; conserva búsqueda y categoría
  al cambiar de página.
- Carga conjunta de autores, editorial y categoría para evitar consultas
  adicionales por cada tarjeta.
- Consulta de disponibilidad y detalle del libro con autores ordenados
  y ejemplares paginados.
- Pantallas propias para crear y editar libros y ejemplares.
- Gestión de autores, categorías y editoriales desde la aplicación.
- Gestión del acervo disponible para el rol bibliotecario sin exigir
  permisos de Django Admin.
- Listados de gestión paginados en grupos de 15 registros.
- Inactivación de libros y baja de ejemplares conservando su historial.
- Protección frente a inactivaciones o estados incompatibles con préstamos
  y reservas vigentes.
- Conservación del código de inventario y del libro de un ejemplar existente.
- Reasignación a la siguiente reserva al habilitar un ejemplar disponible.
- Protección contra la eliminación de autores, categorías o editoriales
  asociados a libros.
- Portada opcional; cuando no se registra, las tarjetas muestran el título
  sobre el fondo del catálogo.
- Django Admin continúa disponible como herramienta administrativa adicional.
- Sugerencias de adquisición de profesores y revisión del bibliotecario.
- Aprobación y rechazo mediante POST con CSRF; una sugerencia procesada
  conserva la decisión registrada.

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
El plazo de 48 horas es para recoger una solicitud o reserva: no es el
plazo de devolución. Los 7 o 30 días empiezan al registrar la entrega física.
En mostrador se registra directamente un préstamo activo.
El vencimiento de una renovación se calcula desde el día en que se renueva.

La aplicación utiliza la política guardada en MySQL. Los valores iniciales
de la tabla no reemplazan una política modificada. Antes de la demostración,
revisar los límites vigentes desde la cuenta del bibliotecario.

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
.\.venv\Scripts\python.exe -m pip check
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
import os

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.environ.get("DB_NAME", "biblioteca"),
        "USER": os.environ.get("DB_USER", "root"),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "HOST": os.environ.get("DB_HOST", "127.0.0.1"),
        "PORT": os.environ.get("DB_PORT", "3306"),
        "OPTIONS": {
            "charset": "utf8mb4",
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

Si se prefiere un archivo `.env`, guardarlo junto a `manage.py` y añadir
la carga en `config/settings.py`, después de definir `BASE_DIR` y antes
de leer las variables de `DATABASES`:

```python
from dotenv import load_dotenv

load_dotenv(BASE_DIR / ".env")
```

El `.env` debe estar incluido en `.gitignore`. No subir contraseñas ni
credenciales personales al repositorio. Si ya existe una carga de variables,
conservar una sola configuración coherente.

### Portadas y archivos de medios

La configuración local en `config/settings.py` debe incluir:

```python
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
```

En `config/urls.py`, importar:

```python
from django.conf import settings
from django.conf.urls.static import static
```

Después de definir `urlpatterns`, añadir para el servidor de desarrollo:

```python
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
```

La carpeta `media` va en la raíz, junto a `manage.py`; `portadas` va dentro
de `media`. Por ejemplo: `media/portadas/portada1.jpg`.
Si una instalación anterior guardó las imágenes en `portadas/` en la raíz,
conservar esos archivos y mover la carpeta a `media/portadas/`, sin cambiar
sus nombres ni sobrescribir archivos existentes. Conservar las portadas
al respaldar o trasladar la demostración.

Esta configuración sirve imágenes con `runserver` y `DEBUG=True`.
Un despliegue público requiere configurar su propio servicio de medios.

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

## Volver a iniciar después de cerrar la terminal

Iniciar MySQL y abrir PowerShell en la raíz del proyecto. Si la conexión
depende de variables de entorno, volver a cargarlas antes de `runserver`.
Si se configuró la credencial local protegida que utiliza la tarea de Windows:

```powershell
$credencialMySQL = Import-Clixml -LiteralPath "$env:LOCALAPPDATA\BiblioEscolar\mysql.credential.xml"
$env:DB_USER = $credencialMySQL.UserName
$env:DB_PASSWORD = $credencialMySQL.GetNetworkCredential().Password
Remove-Variable credencialMySQL
.\.venv\Scripts\python.exe manage.py runserver
```

La credencial debe existir y haber sido creada por el mismo usuario de
Windows en ese equipo, siguiendo `docs/tareas_windows.md`. Si no existe,
utilizar la captura oculta de contraseña del apartado de instalación o la
carga de `.env` ya configurada. No es necesario repetir la población de datos.

## Datos de demostración

Después de aplicar las migraciones, ejecutar desde la raíz del proyecto,
en una terminal con las credenciales locales de MySQL cargadas:

```powershell
.\.venv\Scripts\python.exe poblar_libros.py
.\.venv\Scripts\python.exe poblar_usuarios.py
```

Los scripts preparan el catálogo y las cuentas; no sustituyen las
migraciones ni copian los préstamos de otro equipo.

### Catálogo

- `poblar_libros.py` completa hasta alcanzar 100 libros en total.
- Cada título nuevo recibe un ejemplar con código de inventario único.
- Conserva los libros, ejemplares y operaciones que ya existían.
- Si ya hay 100 libros o más, no añade otros.
- La segunda ejecución comprobada mantuvo 100 libros y 100 ejemplares,
  con 0 registros nuevos.
- Los títulos adicionales usan identificadores `DEMO...` de 13 caracteres
  en el campo ISBN, editorial y edición de demostración, y costo de
  reposición de ejemplo de $300. Estos identificadores no son ISBN comerciales.
- En obras con varios autores, la lista de demostración registra un autor
  principal. Los formularios permiten asociar varios autores.

Las portadas se pueden cargar desde la edición del libro. Los scripts
no descargan imágenes de Internet.

### Cuentas

`poblar_usuarios.py` prepara estas cuentas y sus perfiles:

| Rol | Cuentas definidas en el script | Ejemplos de usuario |
| --- | ---: | --- |
| Estudiante | 20 | `denisse`, `francisco`, `ana_torres`, `luis_garcia` |
| Profesor | 5 | `carolina_romero`, `ricardo_vega`, `patricia_salazar`, `fernando_cruz`, `monica_herrera` |
| Bibliotecario | 2 | `laura_medina`, `roberto_santos` |

Contraseña inicial de las **cuentas nuevas** de demostración:

```text
BibliotecaDemo2026!
```

Las cuentas existentes conservan sus nombres, correos y contraseñas.
Si ya existían `denisse` o `francisco`, su contraseña puede ser distinta
de la indicada. El script no restablece contraseñas ni elimina usuarios.

La carga crea la carrera `ISW` y el departamento `Sistemas y Computación`
si todavía no existen. Si encuentra un nombre de usuario ocupado por otro
rol o una colisión de datos que impide completar perfiles, revierte esa
carga e informa el error.

Los bibliotecarios de demostración acceden a las pantallas del sistema;
no se convierten en superusuarios ni reciben acceso a Django Admin.
Los correos generados son direcciones de ejemplo.

### Políticas

Revisar las políticas desde **Inicio → Administración → Políticas de
préstamo**. La tabla de este documento describe los valores iniciales;
los formularios permiten cambiarlos.

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

## Recuperación de contraseña en la demostración

El proyecto utiliza el backend de consola de Django. En la configuración
local debe estar seleccionado:

```python
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
```

Flujo de recuperación:

1. Abrir **¿Olvidaste tu contraseña?** en el inicio de sesión.
2. Introducir el correo registrado en una cuenta activa que tenga
   contraseña de acceso al sistema.
3. Consultar el mensaje y el enlace que aparecen en la terminal donde
   se está ejecutando `runserver`.
4. Abrir el enlace, definir una nueva contraseña e iniciar sesión con ella.

El enlace incluye un token de recuperación. Si el correo no corresponde
a una cuenta elegible, la pantalla mantiene una respuesta genérica.
Este modo no envía mensajes a Gmail ni a otros buzones: el enlace se
consulta en la terminal. Para la demostración local, mantener el servidor
encendido mientras se abre el enlace.

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

Ejecutar la suite completa:

```powershell
.\.venv\Scripts\python.exe manage.py test --verbosity 1
```

Resultado verificado en MySQL: **97 pruebas aprobadas**.

| Archivo | Pruebas | Cobertura principal |
| --- | ---: | --- |
| `prestamos/tests.py` | 27 | Solicitudes, elegibilidad, renovaciones, permisos y solicitudes concurrentes. |
| `prestamos/test_devoluciones.py` | 13 | Devoluciones, incidencias, reservas y procesamiento de vencimientos. |
| `multas/tests.py` | 20 | Pagos, condonaciones, permisos, CSRF y operaciones simultáneas. |
| `catalogo/test_rendimiento.py` | 3 | Paginación, consultas y tiempos de búsqueda con 10 000 libros. |
| `catalogo/test_sugerencias.py` | 8 | POST, roles, CSRF y conservación de la primera decisión. |
| `catalogo/test_acervo.py` | 26 | Formularios, inventario, historial, reservas, permisos, portadas y navegación. |
| **Total** | **97** | |

Para ejecutar solo la comprobación de rendimiento:

```powershell
.\.venv\Scripts\python.exe manage.py test catalogo.test_rendimiento --verbosity 2
```

Esta prueba genera 10 000 libros con ejemplares y relaciones de autor en
la base temporal. Comprueba búsquedas por título, autor, ISBN, categoría
y sin resultados. Registra el máximo de tres peticiones por caso y exige
menos de 2 segundos en cada uno. Los casos probados cumplieron ese límite
en el equipo utilizado.

Se mide la respuesta de Django, incluida la generación del HTML mediante
su cliente de pruebas. La medición no incluye la descarga de imágenes,
la red ni el renderizado del navegador, y puede variar entre equipos.

El usuario de MySQL necesita permisos para crear y eliminar la base
de pruebas. Django utiliza una base separada, normalmente con el prefijo
`test_`, y la elimina al finalizar una ejecución normal. Los 10 000 libros
de rendimiento no se incorporan al catálogo de demostración.

Otras comprobaciones de cierre:

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
git diff --check
```

Los resultados cubren los escenarios implementados en esos archivos;
no representan una auditoría exhaustiva de todos los permisos o de todas
las combinaciones posibles de concurrencia.

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
| `/catalogo/gestion/` | Gestión del acervo, incluidos libros inactivos |
| `/catalogo/gestion/libros/nuevo/` | Crear libro |
| `/catalogo/gestion/libros/<id>/editar/` | Editar libro |
| `/catalogo/gestion/libros/<id>/ejemplares/` | Gestionar ejemplares de un libro |
| `/catalogo/gestion/datos/autores/` | Autores |
| `/catalogo/gestion/datos/categorias/` | Categorías |
| `/catalogo/gestion/datos/editoriales/` | Editoriales |
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
| `/notificaciones/` | Notificaciones propias |

Las rutas con identificadores representan registros concretos.
El menú muestra las opciones según el rol.

## Verificaciones de cierre

Se comprobó una instalación independiente con una copia nueva del
repositorio, un entorno virtual nuevo y la base `biblioteca_verificacion`:

- Instalación de dependencias y `pip check` sin incompatibilidades.
- Comprobación de Django y aplicación de las migraciones existentes.
- Carga inicial de 100 libros y sus ejemplares.
- Creación de una cuenta administrativa con rol bibliotecario.
- Inicio de sesión y acceso al catálogo en el puerto 8001.

En el proyecto principal también se verificaron la suite de 97 pruebas,
la carga repetida de libros sin duplicados y la apertura de las pantallas
de gestión del acervo. Los cambios visuales posteriores reorganizan los
accesos del inicio y conservan el filtro desplegable de categorías.

## Entrega final al profesor

El equipo enviará al correo del profesor un archivo ZIP que contendrá:

1. **Documento integrado en PDF** con la documentación del proyecto.
2. **Archivos UML de Visual Paradigm (`.vpp`)** elaborados por el equipo.
3. **Carpeta del proyecto Django**, con código fuente, migraciones,
   plantillas, dependencias declaradas, scripts, pruebas y README.
4. **Enlace del repositorio**, incluido en un archivo de texto dentro del ZIP:
   https://github.com/Sonorous06/SitemaDeBibliooteca-Django

El PDF y los archivos `.vpp` se entregarán como documentos separados dentro
del ZIP; sus diagramas no se incluyen en este README.

La carpeta del proyecto debe permitir instalar las dependencias y cargar
los datos de demostración con las instrucciones anteriores. Si se incluyen
portadas, conservar `media/portadas/`. Las credenciales personales, el archivo
`.env`, el entorno virtual `.venv` y los registros locales de ejecución
quedan fuera del paquete de entrega. Cada equipo receptor configura su
propia conexión a MySQL.

El envío por correo y la presentación en vivo se realizan por el equipo;
este apartado describe la organización de esa entrega.

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