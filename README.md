
#  Sistema de Gestión de Biblioteca Escolar - Versión 2.0

Un sistema web completo y robusto desarrollado con **Django 5.x**, **Python 3.12** y **MySQL 8.x** para la automatización integral de la operación de una biblioteca escolar: administración del catálogo bibliográfico, control transaccional de préstamos y devoluciones, cálculo de multas, gestión de reservas en cola FIFO y administración de usuarios por roles.

---

##  Tabla de Contenidos

- [Características Principales](#-características-principales)
- [Reglas de Negocio Implementadas](#-reglas-de-negocio-implementadas)
- [Stack Tecnológico](#-stack-tecnológico)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [Requisitos Previos e Instalación](#-requisitos-previos-e-instalación)
- [Configuración de Base de Datos](#-configuración-de-base-de-datos)
- [Tareas en Segundo Plano](#-tareas-en-segundo-plano)
- [Trabajo Pendiente](#-trabajo-pendiente)
- [Licencia](#-licencia)

---

##  Características Principales

###  1. Autenticación y Gestión de Usuarios (`cuentas`)
- **Control de Roles**: Soporte multi-rol para **Estudiantes**, **Profesores** y **Bibliotecarios** mediante un modelo personalizado (`Usuario` que extiende `AbstractUser`).
- **Elegibilidad Transaccional**: Verificación en tiempo real del estado de cuenta (`bloqueado`, multas pendientes o préstamos vencidos).
- **Gestión Administrativa (`CU-20` / `CU-22`)**: Interfaz exclusiva para bibliotecarios con lista general de usuarios y alternancia de bloqueo administrativo en un solo clic.
- **Recuperación de Contraseña Personalizada (`CU-03`)**: Flujo seguro con token dinámico y envío de enlace de restablecimiento vía correo electrónico (configurable para Gmail SMTP o Consola).

###  2. Catálogo Bibliográfico (`catalogo`)
- **Búsqueda Multicriterio (`CU-04`)**: Filtrado en tiempo real por título, autor, ISBN, editorial y categoría temática.
- **Gestión de Ejemplares Físicos (`CU-18`)**: Seguimiento individualizado de cada copia física (`DISPONIBLE`, `RESERVADO`, `PRESTADO`, `EN_REPARACION`, `PERDIDO`, `BAJA`).
- **Sugerencias de Adquisición (`CU-16` / `CU-33`)**: Módulo para que docentes y alumnos soliciten la compra de nuevos títulos para revisión del bibliotecario.

###  3. Préstamos y Reservas (`prestamos`)
- **Parámetros Configurables (`PoliticaPrestamo`)**: Definición de plazos (7 días para alumnos, 30 días para profesores), topes de libros simultáneos y límite de renovaciones sin modificar código fuente.
- **Reserva y Entrega en Mostrador (`CU-06`, `CU-23`, `CU-24`)**: Solicitud previa de ejemplares en línea y confirmación de entrega física por el bibliotecario.
- **Cola FIFO de Reservas (`RN-12`, `CU-11`, `CU-30`)**: Reasignación automática del ejemplar al primer usuario en lista de espera al registrarse una devolución.
- **Renovación con Validaciones (`CU-10`)**: Extensión de plazo respetando topes máximos y verificación de ausencia de reservas activas por terceros (`RN-04`, `RN-06`).

###  4. Multas y Condonaciones (`multas`)
- **Cálculo Automático por Mora (`RN-07`, `CU-26`)**: Tarifa diaria de penalización por entrega tardía con tope máximo predeterminado.
- **Sanciones por Daño o Pérdida (`RN-13`, `CU-27`)**: Registro de multas equivalentes al costo de reposición del libro.
- **Cobro y Condonación (`CU-28`, `CU-29`)**: Registro de pagos en mostrador (efectivo, transferencia) y condonación justificada por parte del personal autorizado.

###  5. Tareas Programadas y Notificaciones (`notificaciones`)
- **Comando de Fondo (`CU-34` a `CU-36`)**: Ejecución automatizada (`python manage.py procesar_vencimientos`) para aplicar multas diarias, marcar préstamos vencidos y expirar reservas no recogidas a tiempo.

---

##  Reglas de Negocio Implementadas

| Regla | Descripción |
| :--- | :--- |
| **RN-01** | Límite máximo de préstamos activos simultáneos según el tipo de usuario. |
| **RN-02** | Duración de préstamo diferenciada (Estudiantes: 7 días, Profesores: 30 días). |
| **RN-03** | Bloqueo de nuevos préstamos si el usuario tiene multas impagas o libros vencidos. |
| **RN-04** | Prohibición de renovación si el libro ha sido reservado por otro usuario. |
| **RN-06** | Límite máximo de renovaciones consecutivas por préstamo. |
| **RN-07** | Generación de multa diaria acumulativa por cada día de mora. |
| **RN-08** | Inhabilitación automática del usuario al acumular estado bloqueado. |
| **RN-12** | Prioridad estricta FIFO (First In, First Out) en la asignación de reservas. |
| **RN-13** | Multa equivalente al valor de reposición por libros dañados o perdidos. |

---

##  Stack Tecnológico

- **Backend**: Python 3.12 + Django 5.x
- **Base de Datos**: MySQL 8.x (Motor InnoDB, `utf8mb4`)
- **Frontend**: HTML5, Tailwind CSS 3.x, JavaScript (Vanilla ES6)
- **Conector DB**: `mysqlclient` / `PyMySQL`
- **Control de Versiones**: Git & GitHub

---

##  Estructura del Proyecto

```text
biblioteca_escolar/
├── config/                  # Configuración principal del proyecto Django
│   ├── settings.py          # Variables globales, DB, Email y Apps instaladas
│   ├── urls.py              # Enrutador principal de URLs
│   └── wsgi.py
├── cuentas/                 # App de Usuarios, Autenticación y Perfiles
│   ├── models.py            # Modelo Usuario personalizado (AbstractUser)
│   ├── views.py             # Login, Registro, Bloqueos y Password Reset
│   ├── forms.py             # Formularios de autenticación
│   └── urls.py
├── catalogo/                # App de Libros, Categorías y Ejemplares
│   ├── models.py            # Libro, Categoria, Ejemplar, SugerenciaAdquisicion
│   ├── views.py             # Búsqueda, Detalle y Gestión del Catálogo
│   └── urls.py
├── prestamos/               # App de Préstamos, Renovaciones y Reservas
│   ├── models.py            # Prestamo, Reserva, PoliticaPrestamo
│   ├── views.py             # Transacciones de entrega, devolución y reserva
│   └── urls.py
├── multas/                  # App de Control Financiero y Sanciones
│   ├── models.py            # Multa, PagoMulta
│   ├── views.py             # Registro de cobros y condonaciones
│   └── urls.py
├── notificaciones/          # App de Alertas y Tareas en Segundo Plano
│   └── management/
│       └── commands/
│           └── procesar_vencimientos.py
├── templates/               # Plantillas HTML globales

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
>>>>>>> origin/master
├── manage.py
└── README.md
```

---

##  Requisitos Previos e Instalación

### 1. Clonar el Repositorio
```bash
git clone <URL_DEL_REPOSITORIO>
cd biblioteca_escolar
```

### 2. Crear y Activar el Entorno Virtual
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar Dependencias
```bash
pip install -r requirements.txt
```

---

##  Configuración de Base de Datos

1. Crear la base de datos en MySQL:
```sql
CREATE DATABASE bd_biblioteca CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

2. Configurar credenciales en `config/settings.py`:
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
        'NAME': 'bd_biblioteca',
        'USER': 'root',
        'PASSWORD': 'tu_password',
        'HOST': 'localhost',
        'PORT': '3306',
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

3. Aplicar migraciones y crear superusuario:
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

4. Iniciar el servidor de desarrollo:
```bash
python manage.py runserver
```

---

##  Tareas en Segundo Plano

Para ejecutar el proceso automático de cálculo de multas y vencimientos:

```bash
python manage.py procesar_vencimientos
```

---

## Carga de Datos de Prueba

Para poblar la base de datos con información inicial:

```
python poblar_libros.py
python poblar_usuarios.py

```

### Cuentas de prueba:

| Rol               | Usuario     | Contraseña     | Detalles                      |
| ----------------- | ----------- | -------------- | ----------------------------- |
| **Bibliotecario** | `santiago`  | `santiago123`  | Personal de biblioteca        |
| **Profesor**      | `nahomi`    | `nahomi123`    | Depto: Sistemas y Computación |
| **Estudiante**    | `denisse`   | `denisse123`   | Carrera: Ing. en Software     |
| **Estudiante**    | `francisco` | `francisco123` | Carrera: Ing. en Software     |

##  Trabajo Pendiente

###  Completado recientemente:
- [x] **Aplicación `notificaciones` y comando `procesar_vencimientos`**: Se implementó la aplicación de notificaciones y el comando en segundo plano para procesar vencimientos de préstamos, aplicar multas acumuladas y expirar reservas no recogidas a tiempo.
- [x] **Archivo `requirements.txt`**: Se incorporó el archivo de dependencias para unificar la configuración local del equipo.

###  Pendiente por realizar:
- [ ] **Gestión de Reservas FIFO**: Completar creación, consulta, cancelación y recogida de reservas y probar su orden FIFO. (La devolución ya contempla la asignación a reservas pendientes existentes).
- [ ] **Renovaciones**: Implementar renovaciones y sus validaciones.
- [ ] **Sanciones**: Completar el registro de daños y pérdidas y sus sanciones.
- [ ] **Pruebas**: Ampliar pruebas de permisos, políticas y operaciones simultáneas.

---
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

