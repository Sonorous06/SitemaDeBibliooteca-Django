# Sistema de Gestión de Biblioteca Escolar

Proyecto académico desarrollado con Python, Django y MySQL. Permite consultar el catálogo, solicitar y entregar préstamos, registrar devoluciones y gestionar multas, pagos y condonaciones mediante cuentas de estudiante, profesor y bibliotecario. Se ejecuta localmente sin Docker.

## Funciones disponibles

### Cuentas y acceso

- Inicio y cierre de sesión.
- Recuperación de contraseña mediante enlace con token, mensaje de éxito y retorno al inicio de sesión.
- Consulta de usuarios para el bibliotecario.
- Bloqueo con motivo obligatorio y desbloqueo de cuentas.
- Protección contra el bloqueo de la propia cuenta del bibliotecario.
- Validación de bloqueo, multas pendientes y préstamos marcados como vencidos al solicitar préstamos.

### Catálogo y sugerencias

- Consulta de libros activos y filtro por categoría.
- Búsqueda por título, ISBN, autor y editorial.
- Administración de libros y ejemplares desde el administrador de Django.
- Sugerencias de adquisición enviadas por profesores y revisadas por bibliotecarios.

### Préstamos y devoluciones

- Solicitud de un ejemplar disponible desde el catálogo.
- Historial personal en **Mis préstamos**.
- Pantalla de solicitudes pendientes y entrega en mostrador.
- Registro de quién entrega, fecha de préstamo y vencimiento.
- Pantalla de devoluciones y registro de quién recibe el ejemplar.
- Cálculo de multa por retraso al registrar la devolución.
- Asignación del ejemplar devuelto a la primera reserva pendiente existente; si no hay reservas, queda disponible.

### Multas

- **Mis multas** muestra las multas propias, motivo, libro, fecha, importe, estado y total pendiente.
- El acceso permanece visible en el menú del lector aunque el saldo sea cero.
- Liquidación en mostrador mediante efectivo, tarjeta o transferencia.
- Folio automático y registro del bibliotecario que recibe el pago.
- Condonación con justificación obligatoria y registro de quién autoriza.
- Historial de multas pagadas y condonadas; la justificación se muestra al lector.
- Validación del estado dentro de una transacción para impedir repetir un pago o una condonación.

## Roles

| Rol | Acceso principal |
| --- | --- |
| Estudiante | Catálogo, solicitudes, historial de préstamos y multas propias. |
| Profesor | Funciones del lector y envío de sugerencias de adquisición. |
| Bibliotecario | Usuarios, bloqueos, sugerencias, entregas, devoluciones, cobros y condonaciones. |

El rol bibliotecario y el permiso de acceso al administrador de Django son atributos distintos. Para entrar a `/admin/`, la cuenta necesita permisos administrativos.

## Tecnologías

- Python 3.12 y Django 5.2.
- MySQL 8, motor InnoDB y codificación `utf8mb4`.
- `mysqlclient` para la conexión y Pillow para las portadas.
- HTML, Tailwind CSS desde CDN y JavaScript.
- Git y GitHub.

La interfaz necesita conexión a Internet para cargar Tailwind y las fuentes externas.

## Estructura del proyecto

```text
SitemaDeBibliooteca-Django/
├── config/                 # Configuración y rutas principales
├── cuentas/                # Usuario, perfiles, acceso y bloqueos
├── catalogo/               # Libros, autores, categorías y ejemplares
├── prestamos/              # Préstamos, reservas y políticas
├── multas/                 # Multas, pagos y condonaciones
├── templates/              # Plantillas HTML
│   ├── cuentas/
│   ├── catalogo/
│   ├── prestamos/
│   ├── multas/
│   └── registration/
├── crear_tablas.py          # Script auxiliar existente
├── manage.py
└── README.md
```

## Instalación local en Windows

### 1. Descargar el proyecto y crear el entorno

En PowerShell:

```powershell
git clone https://github.com/Sonorous06/SitemaDeBibliooteca-Django.git
cd SitemaDeBibliooteca-Django
python -m venv .venv
```

Si ya tienes el proyecto, abre su carpeta en VS Code y conserva el entorno existente.

### 2. Instalar dependencias

El repositorio todavía no incluye `requirements.txt`. Instala las dependencias utilizadas:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install "Django>=5.2,<5.3" mysqlclient Pillow
```

Estos comandos usan directamente el Python del entorno, sin necesidad de activarlo.

### 3. Preparar MySQL

Inicia el servicio de MySQL. Para una instalación nueva, crea una base vacía desde Workbench:

```sql
CREATE DATABASE biblioteca
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;
```

Si la base ya existe, conserva sus datos y revisa su estructura antes de aplicar cambios.

### 4. Configurar Django

En `config/settings.py`, agrega `import os` junto a los imports y adapta el bloque de conexión:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ.get('DB_NAME', 'biblioteca'),
        'USER': os.environ.get('DB_USER', 'root'),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', '127.0.0.1'),
        'PORT': os.environ.get('DB_PORT', '3306'),
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}
```

Configura también los identificadores automáticos y el correo de desarrollo. Si las opciones ya existen, actualízalas sin duplicarlas:

```python
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
```

Estos son pasos de configuración necesarios al preparar una copia nueva; revisa el `settings.py` compartido antes de ejecutarla. Un archivo `.env` no se carga automáticamente con este procedimiento.

En la terminal donde ejecutarás Django:

```powershell
$env:DB_NAME = "biblioteca"
$env:DB_USER = "root"
$env:DB_PASSWORD = [System.Net.NetworkCredential]::new("", (Read-Host "Contraseña de MySQL" -AsSecureString)).Password
```

Las variables se conservan en esa terminal. Si abres otra para usar el shell o las migraciones, configúralas también allí. Mantén las contraseñas personales fuera de los commits.

### 5. Aplicar migraciones

```powershell
.\.venv\Scripts\python.exe manage.py migrate --plan
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py createsuperuser
```

Cada integrante aplica las migraciones del repositorio en su propia base. Para instalar no es necesario generar migraciones nuevas con `makemigrations`.

Si utilizas una base creada previamente con SQL, compara las tablas y el historial de `django_migrations` antes de continuar. Una migración marcada como aplicada no garantiza que sus tablas existan si el historial se modificó manualmente. No borres tablas ni uses `--fake` sin comprobar que el esquema corresponde a la migración.

### 6. Iniciar el servidor

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py runserver
```

### 7. Carga de Datos de Prueba Una vez aplicadas las migraciones
puedes poblar la base de datos con libros, categorías y usuarios de prueba ejecutando los siguientes scripts en tu terminal con el entorno virtual activo: 

```# 1\. Cargar categorías, editoriales, autores y catálogo de libros
python poblar_libros.py
```
```## 2\. Cargar cuentas de profesor y alumnos python
poblar\_usuarios.py
```
Abre `http://127.0.0.1:8000/`. Detén el servidor con `Ctrl + C`.

## Preparación de datos y políticas

Una base nueva no incluye los usuarios ni los libros de otro integrante. Desde `/admin/`, registra categorías, editoriales, un libro activo y al menos un ejemplar **Disponible** con código de inventario único.

Crea una cuenta activa con tipo **ESTUDIANTE** o **PROFESOR** para probar como lector. Puedes mantener la sesión de bibliotecario en la ventana normal y usar incógnito para el lector.

El modelo `PoliticaPrestamo` almacena días de préstamo, máximo de libros, renovaciones, tarifa diaria, tope de multa y horas de recogida. Configúralo en cada base si deseas aplicar esos parámetros. Las vistas actuales usan estos valores de respaldo cuando no existe una política:

| Parámetro | Valor |
| --- | --- |
| Plazo del estudiante | 7 días |
| Plazo del profesor | 30 días |
| Tiempo para recoger | 48 horas |
| Multa por día de retraso | $10.00 MXN |
| Tope de multa por retraso | $300.00 MXN |

El límite de libros se comprueba cuando existe una política para el tipo de usuario. Los valores de respaldo no crean registros de políticas automáticamente.

## Rutas principales

| Ruta | Función |
| --- | --- |
| `/` | Inicio según el rol. |
| `/admin/` | Administración de Django. |
| `/cuentas/recuperar-password/` | Recuperación de contraseña. |
| `/cuentas/usuarios/` | Usuarios y bloqueos. |
| `/catalogo/` | Catálogo y búsqueda. |
| `/catalogo/sugerencias/` | Revisión de sugerencias. |
| `/prestamos/mis-prestamos/` | Historial del lector. |
| `/prestamos/solicitudes/` | Entregas pendientes. |
| `/prestamos/devoluciones/` | Registro de devoluciones. |
| `/multas/mis-multas/` | Multas propias y saldo pendiente. |
| `/multas/pendientes/` | Cobro y condonación de multas. |

Las operaciones de gestión validan el rol bibliotecario. El inicio de sesión y la recuperación son públicos; las demás pantallas de la aplicación requieren autenticación. El administrador tiene su propio control de permisos.

## Recuperación de contraseña en desarrollo

Con el backend de consola, el mensaje y el enlace aparecen en la terminal de `runserver`; no se envía un correo real. Utiliza el correo registrado de una cuenta activa con contraseña utilizable. La confirmación de solicitud no revela si el correo existe.

Al cambiar la contraseña se muestra el mensaje de éxito y se regresa al inicio de sesión. El envío real por SMTP requiere configuración adicional.

## Pruebas manuales realizadas

Se utilizaron una cuenta de estudiante de prueba y un ejemplar de *El principito*:

| Caso | Resultado observado |
| --- | --- |
| Solicitud con cuenta bloqueada | Mensaje de suspensión con motivo. |
| Solicitud tras desbloquear | Solicitud registrada y pendiente de recogida. |
| Entrega en mostrador | Préstamo activo, ejemplar prestado y vencimiento visible al lector. |
| Devolución a tiempo | Préstamo devuelto y ejemplar disponible, sin multa por retraso. |
| Devolución con tres días de retraso | Multa de $30.00 con la tarifa de respaldo. |
| Consulta personal | Multa y saldo visibles en Mis multas. |
| Pago | Estado Pagada y saldo pendiente de $0.00. |
| Condonación de otra multa | Estado Condonada, justificación visible y saldo de $0.00. |

Son pruebas manuales del flujo principal; no sustituyen pruebas automatizadas ni comprueban todos los casos de concurrencia o permisos.

## Trabajo pendiente

- Completar creación, consulta, cancelación y recogida de reservas y probar su orden FIFO. La devolución ya contempla la asignación a reservas pendientes existentes.
- Implementar renovaciones y sus validaciones.
- Completar el registro de daños y pérdidas y sus sanciones.
- Agregar procesos programados para vencimientos, expiración de solicitudes y reservas y notificaciones.
- Incorporar `requirements.txt` y unificar la configuración local del equipo.
- Ampliar pruebas de permisos, políticas y operaciones simultáneas.

El repositorio actual no incluye una aplicación `notificaciones` ni un comando `procesar_vencimientos`.

## Colaboración

1. Actualizar `main` antes de iniciar una funcionalidad.
2. Trabajar en una rama propia.
3. Probar con los roles correspondientes.
4. Revisar `git status`, el diff y `git diff --cached --check` antes del commit.
5. Subir la rama y crear un pull request hacia `main`.
6. Comprobar que aparezca **Merged** antes de descargar la integración.

Los commits comparten código y migraciones; no transfieren los registros de la base local. Cada integrante aplica las migraciones pendientes en su propia instalación.
