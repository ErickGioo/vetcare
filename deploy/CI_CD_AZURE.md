# CI/CD con GitHub Actions y Azure VM

Este flujo usa GitHub Actions para validar cada cambio y desplegar automáticamente a la VM de Azure cuando llega un cambio a la rama `main`.

```text
Pull request / push  ->  construir imagen + Django check  ->  push a main  ->  SSH a Azure  ->  Docker Compose
```

No se suben secretos, `.env`, archivos de medios ni la base de datos al repositorio. El archivo `.env` de producción vive exclusivamente en `/opt/vetcare/.env` dentro de la VM.

## 1. Preparar el repositorio

1. Sube el proyecto a GitHub y confirma que `.env` está incluido en `.gitignore`.
2. En GitHub ve a **Settings > Environments > New environment** y crea `production`.
3. Si tu plan lo permite, agrega un revisor requerido para aprobar cada despliegue a `production`.

## 2. Crear una clave exclusiva para despliegues

En tu Mac, crea una clave que utilizará únicamente GitHub Actions para entrar a Azure:

```bash
ssh-keygen -t ed25519 -C "github-actions-vetcare" -f ~/.ssh/vetcare_actions
```

Agrega el contenido de `~/.ssh/vetcare_actions.pub` al archivo `~/.ssh/authorized_keys` del usuario de despliegue de la VM:

```bash
ssh vetcareadmin@IP_PUBLICA
mkdir -p ~/.ssh
chmod 700 ~/.ssh
nano ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

Obtén y verifica la huella pública del servidor desde tu Mac:

```bash
ssh-keyscan -H IP_PUBLICA
```

Verifica la huella con la que muestra tu primera conexión SSH conocida antes de guardarla.

## 3. Crear secretos de GitHub

En el entorno **production**, abre **Environment secrets** y agrega estos tres secretos:

| Nombre | Valor |
| --- | --- |
| `DEPLOY_HOST` | IP pública o dominio de la VM |
| `DEPLOY_USER` | `vetcareadmin` (o el usuario que uses) |
| `DEPLOY_SSH_KEY` | Contenido completo de `~/.ssh/vetcare_actions` (clave privada) |
| `DEPLOY_KNOWN_HOSTS` | La línea completa verificada que devolvió `ssh-keyscan -H` |

No agregues `SECRET_KEY`, contraseñas de la base de datos ni claves de NeoNet a GitHub Actions: ya deben estar en `/opt/vetcare/.env`, con permisos `600`.

## 4. Crear el workflow

Crea el archivo `.github/workflows/deploy.yml` en el repositorio con este contenido:

```yaml
name: CI y despliegue a Azure

on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read

concurrency:
  group: vetcare-production
  cancel-in-progress: false

jobs:
  verificar:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Construir imagen
        run: docker build -t vetcare-ci .
      - name: Validar configuración Django
        run: |
          docker run --rm --entrypoint python \
            -e SECRET_KEY='ci-only-not-a-production-secret' \
            -e DEBUG=False \
            -e ALLOWED_HOSTS='example.com' \
            -e CSRF_TRUSTED_ORIGINS='https://example.com' \
            vetcare-ci manage.py check

  desplegar:
    needs: verificar
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: production
    steps:
      - name: Configurar SSH
        env:
          DEPLOY_SSH_KEY: ${{ secrets.DEPLOY_SSH_KEY }}
          DEPLOY_KNOWN_HOSTS: ${{ secrets.DEPLOY_KNOWN_HOSTS }}
        run: |
          install -m 700 -d ~/.ssh
          printf '%s\n' "$DEPLOY_SSH_KEY" > ~/.ssh/id_ed25519
          chmod 600 ~/.ssh/id_ed25519
          printf '%s\n' "$DEPLOY_KNOWN_HOSTS" > ~/.ssh/known_hosts

      - name: Desplegar versión validada
        env:
          DEPLOY_HOST: ${{ secrets.DEPLOY_HOST }}
          DEPLOY_USER: ${{ secrets.DEPLOY_USER }}
        run: |
          ssh -i ~/.ssh/id_ed25519 "$DEPLOY_USER@$DEPLOY_HOST" '
            set -eu
            cd /opt/vetcare
            git fetch origin main
            git checkout main
            git pull --ff-only origin main
            docker compose up --build -d
            docker compose exec -T web python manage.py check
            curl --fail --silent --show-error http://127.0.0.1:8000/healthz/
          '
```

La acción `actions/checkout@v4` se puede fijar a un SHA de commit en vez de una etiqueta para mayor control de la cadena de suministro.

## 5. Preparar una sola vez la VM

En la VM, el proyecto ya debe estar clonado en `/opt/vetcare`, en la rama `main`, y con su `.env` productivo configurado:

```bash
cd /opt/vetcare
git checkout main
docker compose up --build -d
curl --fail http://127.0.0.1:8000/healthz/
```

## 6. Operación diaria

1. Crea una rama para cada cambio y abre un pull request.
2. GitHub ejecuta la validación de la imagen y Django.
3. Fusiona el pull request a `main`.
4. El entorno `production` solicita aprobación, si configuraste revisores.
5. GitHub se conecta a la VM, actualiza el código, reconstruye los contenedores y prueba `/healthz/`.

Si una validación falla, no se ejecuta el despliegue. Para ver el motivo: **GitHub > Actions > CI y despliegue a Azure**.

## Recuperación rápida

En la VM, identifica el commit anterior y vuelve a él si necesitas revertir una versión:

```bash
cd /opt/vetcare
git log --oneline -5
git checkout COMMIT_ANTERIOR
docker compose up --build -d
curl --fail http://127.0.0.1:8000/healthz/
```

Después crea un commit de reversión en GitHub; de otro modo el siguiente despliegue automático volverá a dejar `main` en la versión más reciente.
