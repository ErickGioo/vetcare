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

El flujo de CI/CD para GitHub Actions y una VM de Azure está en [`deploy/CI_CD_AZURE.md`](deploy/CI_CD_AZURE.md).

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

## Flujos de atención, ventas e informes

- **Pantalla TV:** `/citas/tv/` muestra las citas de hoy y sus estados; se actualiza cada 20 segundos. Requiere sesión.
- **Especies y razas:** `/pacientes/catalogos/` permite al administrador ampliar los catálogos. En el registro del paciente, las razas se filtran por especie y primeras letras, con validación también en el servidor.
- **Consultas:** selecciona un servicio con su tarifa. El catálogo se configura una sola vez y se reutiliza: el formulario de consulta no ofrece crear productos ni tarifas. Al guardar la atención se genera una venta pendiente vinculada; el ingreso solo se refleja al confirmar el pago. Las consultas anteriores pueden facturarse desde su detalle, sin generar automáticamente cargos retroactivos.
- **Grooming:** la agenda ofrece Grooming / peluquería, Baño y Corte de uñas. Se puede asignar un profesional responsable o dejarlo pendiente. Las tarifas se configuran como productos de tipo Servicio y se cobran desde Ventas.
- **Revisiones:** al indicar fecha y hora en la consulta o postconsulta, se crea una cita de control pendiente. Las actualizaciones reutilizan la cita vinculada.
- **Corrección de ventas:** en una venta pendiente se puede cambiar la cantidad o quitar artículos. Se ajustan existencias y se registra el movimiento. Las ventas pagadas o con un pago de tarjeta en proceso están protegidas; no hay un flujo de devolución implementado.
- **Servicios:** se venden sin requerir stock físico ni generar movimientos de inventario.
- **Comprobantes:** el detalle de la venta permite imprimir o guardar como PDF un comprobante interno; no es factura fiscal/FEL. El informe para el dueño incluye raza, recomendaciones, revisión y membrete Vetcare; excluye observaciones internas.
- **Informes administrativos:** `/informes/`, `/informes/ventas/`, `/informes/cierres/` e `/informes/inventario/` requieren usuario staff. Los cierres consultan fecha de creación de la venta y estado actual; no son arqueos ni cierres contables inmutables. No se registra una fecha independiente de cobro ni el desglose de los pagos mixtos.
- **Ganancia bruta:** ventas pagadas menos costo histórico de sus artículos. No incluye nómina ni gastos operativos. Los costos de ventas previas a la migración de costo histórico se estiman usando el costo disponible del producto al aplicar la mejora.
- **Mínimo sugerido:** salidas promedio de hasta 90 días completos por los días de entrega y reserva indicados. No cambia el mínimo configurado; sin salidas se informa que no hay historial.

Pruebas de regresión (con dependencias instaladas y una base de pruebas disponible):

```bash
python manage.py test citas pacientes ventas informes
```

En la VM, construir la imagen, respaldar PostgreSQL y aplicar `python manage.py migrate --noinput` antes de reiniciar el servicio. El contenedor también aplica las migraciones al arrancar. El `.env` de producción se conserva únicamente en el servidor. Docker publica el puerto 8000 en localhost para usar el proxy existente. Las opciones de cookies seguras y redirección HTTPS son configurables por entorno y mantienen valores seguros por defecto.

### Control de servicios realizados

En `/informes/servicios/` se cuentan citas con estado Completada por tipo (incluido grooming), con períodos diario, semanal de lunes a domingo y mensual. Se usa la fecha programada de la cita en la zona horaria de la aplicación. El conteo no depende del pago y no crea productos, ventas ni movimientos de inventario. No suma historias clínicas ni ventas a las citas, para evitar duplicar atenciones; las consultas sin cita no se incluyen. Disponible para administradores desde Informes.
