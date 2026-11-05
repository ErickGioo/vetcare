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

### Caja diaria

`/caja/` (administradores) permite apertura del día con fondo inicial, cobros de efectivo/transferencias/tarjeta, conteo y cierre definitivo con diferencias por método, responsables, observaciones e impresión. Una apertura por fecha; debe cerrarse la anterior. La reapertura requiere solicitud y autorización explícita de un administrador. Efectivo esperado = fondo inicial + cobros en efectivo. Transferencias y tarjeta se concilian contra banco/terminal, sin sumarse al efectivo físico. No incluye gastos, retiros, depósitos ni otros movimientos ajenos a ventas.

Cada confirmación de pago guarda un `CobroCaja` único por venta con fecha real de cobro en Guatemala y monto/método conservados. NeoNet solo registra respuestas aceptadas, sin duplicar callbacks. Se serializan cobros, aperturas y cierres en PostgreSQL con una fila de control. Los cierres guardan importes esperados y contados; un cobro posterior queda fuera del cierre, visible como pendiente de conciliar en su fecha. Los cobros de hoy anteriores a la apertura se incorporan al abrir. La caja no cambia el criterio de los informes antiguos de ventas/cierres (fecha de creación de venta).

Los pagos históricos anteriores a este módulo no se reconstruyen con fechas supuestas. Los pagos mixtos nuevos no se confirman hasta disponer de desglose; debe seleccionarse un método único. No se realiza cobro real al abrir o cerrar caja. Un pago NeoNet pendiente impide cerrar para evitar omitir una confirmación en proceso.

`/caja/accesos/` muestra a administradores el usuario, fecha/hora de Guatemala, pantalla/acción, método HTTP y resultado, con filtro diario y paginación. El middleware registra solicitudes autenticadas desde su activación (incluye inicio y cierre de sesión); no almacena parámetros, formularios, IP, credenciales ni datos clínicos. Omite archivos estáticos, salud, búsqueda de razas y refrescos automáticos de TV; sí registra la apertura inicial de TV. No equivale a una auditoría de cambios de campos ni registra intentos de acceso anónimos. Los registros se conservan sin edición o borrado desde la interfaz.

### Reapertura autorizada de caja

En la caja cerrada se solicita reapertura indicando motivo. Solo una cuenta activa de superusuario o de empleado activo con rol Administrador (y acceso staff) puede aprobar o rechazar, mediante POST con CSRF. No se solicitan contraseñas de otro usuario en la caja. Se conserva el cuadre anterior (esperado, contado, observaciones, responsable, fecha y cobros incluidos), quién pidió y quién autorizó, con sus horas. Una solicitud por cierre pendiente; no se aprueba dos veces ni si hay otra caja abierta. Al aprobar se incorporan los cobros sin caja de esa misma fecha y se permite un nuevo cierre, conservando el anterior en el historial de autorizaciones.

### Categorías, códigos y permisos

Productos muestra una sola clasificación: Categoría. Cada categoría configura si corresponde a servicios sin inventario; la migración asigna categorías a registros antiguos y separa categorías que mezclaban servicios y artículos, conservando los códigos y las ventas. La distinción técnica de servicio se mantiene internamente para no descontar stock al facturar una atención. Las categorías con productos no pueden cambiar su manejo de inventario, ni convertir productos existentes entre físico y servicio.

Código es opcional: se genera un identificador único al dejarlo vacío; se admite un código manual o de barras existente. No se renumeran los productos guardados. El ID interno sigue siendo automático.

`PermisosModulosMiddleware` aplica en las pantallas los permisos estándar de Django (ver, añadir, cambiar y eliminar), incluyendo solicitudes directas por URL y POST, además de permisos de usuario y grupos. Ser staff no concede acceso total; solo el superusuario lo tiene. Caja e informes conservan además sus restricciones de administrador; Registro de accesos sigue exclusivo del superusuario. Registrar una consulta facturada requiere añadir historial y venta; agendar una revisión requiere permisos de citas. Los datos asociados de otros módulos se omiten cuando falta su permiso de consulta. Los permisos efectivos se gestionan en Administración → Usuarios/Grupos, sin asignar automáticamente acceso extra a cuentas existentes.

### Almacén central, puntos de venta y distribución

- `/inventario/`: existencias por ubicación y traslados con usuario, fecha, motivo y token para impedir duplicados al repetir la misma solicitud. Los ingresos/ajustes de Productos operan sobre el almacén central. Producto.stock conserva el total disponible de toda la red; las transferencias no cambian ese total. Ventas pendientes siguen reservando stock como en el flujo anterior.
- `/inventario/puntos/`: crea puntos de venta y asigna usuarios. La asignación delimita ubicaciones, pero no concede permisos de ventas/caja. Los usuarios sin asignaciones conservan únicamente el almacén central para compatibilidad; asignarles puntos los limita a esos puntos. El superusuario ve la red completa. Las cuentas actuales no reciben permisos nuevos automáticamente.
- Migración: las existencias disponibles actuales se cargan al almacén central y las ventas/cajas históricas se vinculan a esa ubicación. No se inventan sucursales ni se distribuye mercancía sin un traslado explícito. La migración se detiene si encuentra existencias negativas.
- Cada venta se crea con ubicación fija. Las líneas descuentan de esa ubicación y las correcciones devuelven allí el stock. No se puede vender con el inventario de otro punto. La caja diaria es independiente por punto, incluyendo apertura, cierre, cobros y reapertura. Los informes monetarios se filtran a las ubicaciones permitidas.
- Distribución: `/ventas/?canal=mayorista`. Usa el mismo producto/marca/stock con `precio_mayorista` propio y comprobante de venta. Si no hay tarifa mayorista positiva, la operación se rechaza. No incluye importaciones, fletes, aduanas ni costos de llegada.

### Marcas, proveedores y lector

`/proveedores/marcas/` registra marcas independientes. Un producto tiene una marca y puede tener proveedor principal y varios alternativos; un proveedor puede ofrecer varias marcas. Cambiar de proveedor no crea otro producto ni duplica stock. El código de barras es opcional, único y separado del código interno generado. El lector USB/Bluetooth en modo teclado puede capturarlo al crear un producto, buscar inventario o añadir artículos a una venta. Un código desconocido no crea productos automáticamente. Nombre, marca, categoría y tarifas se configuran la primera vez.

### Aprobación de descuentos desde 5 %

El 5 % inclusive requiere autorización de administrador, también en distribución y puntos de venta. Se comprueba antes de efectivo/transferencia y antes de iniciar NeoNet; aplica también a descuentos del catálogo. La solicitud contiene motivo, porcentaje, total, huella de artículos/precios/cantidades, solicitante y fecha. Cambiar la venta invalida la aprobación anterior. Solo una cuenta activa de superusuario o empleado Administrador activo, con los permisos de solicitud correspondientes, puede aprobar o rechazar en `/ventas/descuentos/`. Nunca se aprueba por visitar un enlace GET.

Sin proveedor WhatsApp contratado, el botón genera un mensaje para compartir manualmente y elegir al administrador en WhatsApp. El usuario debe enviarlo; el sistema no afirma haber entregado el mensaje. El administrador inicia sesión en Vetcare y autoriza allí. No hay SMS, envío automático, credenciales de WhatsApp Business ni cargos de mensajería configurados. Las ventas/pagos del administrador Django quedan de consulta para impedir saltarse aprobación, stock o registro de caja; las operaciones se realizan desde las pantallas de Vetcare.
