# Sistema de Gestión de Biblioteca Escolar

Un sistema web completo y robusto desarrollado con **Django 5.x**, **Python 3.12** y **MySQL 8.x** para la automatización integral de la operación de una biblioteca escolar: administración del catálogo bibliográfico, control transaccional de préstamos y devoluciones, cálculo de multas, gestión de reservas en cola FIFO y administración de usuarios por roles.

---

## Tabla de Contenidos

* [Características Principales](#-caracter%C3%ADsticas-principales)
* [Reglas de Negocio Implementadas](#-reglas-de-negocio-implementadas)
* [Stack Tecnológico](#-stack-tecnol%C3%B3gico)
* [Estructura del Proyecto](#-estructura-del-proyecto)
* [Requisitos Previos e Instalación](#-requisitos-previos-e-instalaci%C3%B3n)
* [Configuración de Base de Datos](#-configuraci%C3%B3n-de-base-de-datos)
* [Tareas en Segundo Plano](#-tareas-en-segundo-plano)

---

## Características Principales

### 1\. Autenticación y Gestión de Usuarios (`cuentas`)

* **Control de Roles**: Soporte multi-rol para **Estudiantes**, **Profesores** y **Bibliotecarios** mediante un modelo personalizado (`Usuario` que extiende `AbstractUser`).
* **Elegibilidad Transaccional**: Verificación en tiempo real del estado de cuenta (`bloqueado`, multas pendientes o préstamos vencidos).
* **Gestión Administrativa (`CU-20` / `CU-22`)**: Interfaz exclusiva para bibliotecarios con lista general de usuarios y alternancia de bloqueo administrativo en un solo clic.
* **Recuperación de Contraseña Personalizada (`CU-03`)**: Flujo seguro con token dinámico y envío de enlace de restablecimiento vía correo electrónico (configurable para Gmail SMTP o Consola).

### \. Catálogo Bibliográfico (`catalogo`)

* **Búsqueda Multicriterio (`CU-04`)**: Filtrado en tiempo real por título, autor, ISBN, editorial y categoría temática.
* **Gestión de Ejemplares Físicos (`CU-18`)**: Seguimiento individualizado de cada copia física (`DISPONIBLE`, `RESERVADO`, `PRESTADO`, `EN_REPARACION`, `PERDIDO`, `BAJA`).
* **Sugerencias de Adquisición (`CU-16` / `CU-33`)**: Módulo para que docentes y alumnos soliciten la compra de nuevos títulos para revisión del bibliotecario.

### \. Préstamos y Reservas (`prestamos`)

* **Parámetros Configurables (`PoliticaPrestamo`)**: Definición de plazos (7 días para alumnos, 30 días para profesores), topes de libros simultáneos y límite de renovaciones sin modificar código fuente.
* **Reserva y Entrega en Mostrador (`CU-06`, `CU-23`, `CU-24`)**: Solicitud previa de ejemplares en línea y confirmación de entrega física por el bibliotecario.
* **Cola FIFO de Reservas (`RN-12`, `CU-11`, `CU-30`)**: Reasignación automática del ejemplar al primer usuario en lista de espera al registrarse una devolución.
* **Renovación con Validaciones (`CU-10`)**: Extensión de plazo respetando topes máximos y verificación de ausencia de reservas activas por terceros (`RN-04`, `RN-06`).

### \. Multas y Condonaciones (`multas`)

* **Cálculo Automático por Mora (`RN-07`, `CU-26`)**: Tarifa diaria de penalización por entrega tardía con tope máximo predeterminado.
* **Sanciones por Daño o Pérdida (`RN-13`, `CU-27`)**: Registro de multas equivalentes al costo de reposición del libro.
* **Cobro y Condonación (`CU-28`, `CU-29`)**: Registro de pagos en mostrador (efectivo, transferencia) y condonación justificada por parte del personal autorizado.

### 5\. Tareas Programadas y Notificaciones (`notificaciones`)

* **Comando de Fondo (`CU-34` a `CU-36`)**: Ejecución automatizada (`python manage.py procesar_vencimientos`) para aplicar multas diarias, marcar préstamos vencidos y expirar reservas no recogidas a tiempo.

---

## Reglas de Negocio Implementadas

| Regla     | Descripción                                                                       |
| --------- | --------------------------------------------------------------------------------- |
| **RN-01** | Límite máximo de préstamos activos simultáneos según el tipo de usuario.          |
| **RN-02** | Duración de préstamo diferenciada (Estudiantes: 7 días, Profesores: 30 días).     |
| **RN-03** | Bloqueo de nuevos préstamos si el usuario tiene multas impagas o libros vencidos. |
| **RN-04** | Prohibición de renovación si el libro ha sido reservado por otro usuario.         |
| **RN-06** | Límite máximo de renovaciones consecutivas por préstamo.                          |
| **RN-07** | Generación de multa diaria acumulativa por cada día de mora.                      |
| **RN-08** | Inhabilitación automática del usuario al acumular estado bloqueado.               |
| **RN-12** | Prioridad estricta FIFO (First In, First Out) en la asignación de reservas.       |
| **RN-13** | Multa equivalente al valor de reposición por libros dañados o perdidos.           |

---

## Stack Tecnológico

* **Backend**: Python 3.12 + Django 5.x
* **Base de Datos**: MySQL 8.x (Motor InnoDB, `utf8mb4`)
* **Frontend**: HTML5, Tailwind CSS 3.x, JavaScript (Vanilla ES6)
* **Conector DB**: `mysqlclient` / `PyMySQL`
* **Control de Versiones**: Git & GitHub

---

##  
Estructura del Proyecto

```
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
├── manage.py
└── README.md
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

## Configuración de Base de Datos

1. Crear la base de datos en MySQL:
```sql
CREATE DATABASE bd_biblioteca CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

2. Configurar credenciales en `config/settings.py`:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'bd_biblioteca',
        'USER': 'root',
        'PASSWORD': 'tu_password',
        'HOST': 'localhost',
        'PORT': '3306',
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

## Tareas en Segundo Plano

Para ejecutar el proceso automático de cálculo de multas y vencimientos:

```bash
python manage.py procesar_vencimientos
```
