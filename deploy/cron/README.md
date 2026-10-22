# Arranque automático de VetCare con cron

Este cron inicia todos los servicios de `docker-compose.yml`: PostgreSQL y la aplicación web. El contenedor web ejecuta las migraciones y `collectstatic` automáticamente mediante `docker/entrypoint.sh`.

## 1. Dar permiso al script

```bash
cd "/Users/erick/vetcare/vetcare 2"
chmod +x deploy/cron/vetcare-start.sh
```

## 2. Registrar el cron de arranque

Abra el editor de cron de su usuario:

```bash
crontab -e
```

Agregue esta línea al final:

```cron
@reboot /Users/erick/vetcare/vetcare\ 2/deploy/cron/vetcare-start.sh
```

Guarde el archivo y confirme la tarea:

```bash
crontab -l
```

## 3. Prueba sin reiniciar

```bash
"/Users/erick/vetcare/vetcare 2/deploy/cron/vetcare-start.sh"
docker compose -f "/Users/erick/vetcare/vetcare 2/docker-compose.yml" ps
```

El registro se guarda en `logs/vetcare-start.log`.

## Importante en macOS

Cron solo puede levantar los contenedores si Docker Desktop ya está abierto y listo. Active **Start Docker Desktop when you log in** en Docker Desktop → Settings → General. Para un arranque antes de iniciar sesión, `launchd` es más adecuado que cron.
