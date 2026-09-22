# Despliegue en AWS (produccion)

Arquitectura recomendada: **ECR -> ECS Fargate (subredes privadas) -> Application Load Balancer publico**, con **RDS PostgreSQL** privado, secretos en **Secrets Manager** y archivos de `media/` en S3 (pendiente de configurar antes de usar cargas de archivos en produccion).

## 1. Base de datos y secretos

1. Crea una instancia RDS PostgreSQL en subredes privadas. Autoriza el puerto 5432 en su grupo de seguridad solo desde el grupo de seguridad de ECS.
2. Crea un secreto de Secrets Manager con las claves `SECRET_KEY` y `DB_PASSWORD`.
3. Crea los roles `ecsTaskExecutionRole` (con acceso a ECR, CloudWatch Logs y al secreto) y un `taskRole` con los permisos mínimos necesarios. Si se configura S3 para media, concede solo acceso al bucket y prefijo correspondientes.

## 2. Imagen y repositorio ECR

Desde la raíz del proyecto, reemplaza los marcadores y ejecuta:

```bash
aws ecr create-repository --repository-name vetcare --region REGION
aws ecr get-login-password --region REGION | docker login --username AWS --password-stdin ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com
docker build -t vetcare:TAG .
docker tag vetcare:TAG ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com/vetcare:TAG
docker push ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com/vetcare:TAG
```

## 3. ECS y ALB

1. Crea un cluster ECS y un servicio Fargate en al menos dos subredes privadas. Registra la definición de tarea de este directorio tras sustituir todos los valores `REEMPLAZAR_*`.
2. Crea un ALB público con certificado ACM en 443. El target group debe usar HTTP, puerto 8000 y health check `/healthz/`.
3. El grupo de seguridad del ALB permite 443 desde Internet; el de ECS permite 8000 únicamente desde el ALB.
4. Configura `ALLOWED_HOSTS` con el DNS del ALB y los dominios finales, y `CSRF_TRUSTED_ORIGINS` con esos dominios completos (`https://...`).

La tarea aplica migraciones automáticamente durante el arranque. Para despliegues con varias tareas, ejecuta las migraciones como tarea ECS única antes de escalar el servicio para evitar ejecuciones simultáneas.

## 4. Operacion

Activa copias de seguridad automáticas y Multi-AZ para RDS según el nivel de disponibilidad requerido; conserva logs de CloudWatch y crea alertas de errores/CPU. No uses el volumen local del contenedor para archivos de usuarios: Fargate es efímero; configura almacenamiento S3 antes de habilitar media en producción.
