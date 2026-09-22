# 🐾 VetCare — Sistema de Gestión Veterinaria

Sistema completo desarrollado con **Django + PostgreSQL** para la gestión de una clínica veterinaria.

---

## ⚙️ Instalación paso a paso

## 🐳 Ejecutar con Docker

1. Crea el archivo de variables y asigna una contraseña segura:

```bash
cp .env.example .env
# Edita .env y define DB_PASSWORD y SECRET_KEY. Puedes generar la clave con:
# python -c "import secrets; print(secrets.token_urlsafe(50))"
docker compose up --build
```

La aplicación queda disponible en `http://localhost:8000` y su verificación de salud en `http://localhost:8000/healthz/`. Para detenerla, ejecuta `docker compose down`; añade `-v` solamente si deseas eliminar también los datos locales de PostgreSQL.

La guía y plantilla para AWS ECS Fargate + RDS están en [`deploy/aws/README.md`](deploy/aws/README.md).

La integración de tarjeta con NeoNet/CyberSource se configura siguiendo [`deploy/neonet.md`](deploy/neonet.md).

### 1. Crear y activar ambiente virtual

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / Mac
source venv/bin/activate
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Configurar PostgreSQL

Crear la base de datos en PostgreSQL:

```sql
CREATE DATABASE vetcare_db;
CREATE USER vetcare_user WITH PASSWORD 'tu_password';
GRANT ALL PRIVILEGES ON DATABASE vetcare_db TO vetcare_user;
```

### 4. Configurar variables de entorno

Copia `.env.example` a `.env` y llena tus datos:

```bash
cp .env.example .env
```

Edita `.env`:

```
SECRET_KEY=una-clave-secreta-segura
DEBUG=True
DB_NAME=vetcare_db
DB_USER=vetcare_user
DB_PASSWORD=tu_password
DB_HOST=localhost
DB_PORT=5432
```

### 5. Aplicar migraciones

```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Crear superusuario

```bash
python manage.py createsuperuser
```

### 7. Ejecutar el servidor

```bash
python manage.py runserver
```

Abre: **http://127.0.0.1:8000**

---

## 📋 Módulos del sistema

| Módulo | Funcionalidades |
|--------|----------------|
| **Productos** | CRUD, categorías, control de stock, movimientos de inventario, descuentos |
| **Clientes** | Registro de propietarios con historial de mascotas y ventas |
| **Pacientes** | Ficha clínica + historial médico completo + post-consulta |
| **Proveedores** | Gestión de proveedores ligados a productos |
| **Empleados** | Veterinarios y staff con roles y especialidades |
| **Citas** | Agenda con tipos, estados y cambio rápido |
| **Ventas** | Facturación con detalle por producto y confirmación de pago |
| **Historial** | Registro unificado de todas las transacciones |

---

## 🩺 Módulo Historial Médico (Pacientes)

Cada consulta registra:

- **Datos clínicos**: motivo, anamnesis, examen físico, signos vitales
- **Diagnóstico**: presuntivo y definitivo, exámenes solicitados y resultados
- **Tratamiento**: plan, medicamentos, cirugías
- **Post-consulta** *(el médico completa al finalizar)*:
  - Descripción post-consulta (evolución esperada, notas finales)
  - Recomendaciones al propietario (cuidados en casa, señales de alarma)
- **Seguimiento**: estado (abierta / seguimiento / cerrada), próxima cita

---

## 📁 Estructura

```
vetcare/
├── vetcare/          # Configuración principal (settings, urls)
├── productos/        # App inventario
├── clientes/         # App propietarios
├── pacientes/        # App mascotas + historial médico
├── proveedores/      # App proveedores
├── empleados/        # App personal
├── citas/            # App agenda
├── ventas/           # App facturación
├── templates/        # Templates base y dashboard
├── .env.example      # Variables de entorno ejemplo
├── manage.py
└── requirements.txt
```

---

## 🔐 Acceso

- Sistema: http://127.0.0.1:8000/
- Admin Django: http://127.0.0.1:8000/admin/
