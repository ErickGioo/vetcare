#!/bin/sh
# Arranque seguro de VetCare para cron (@reboot).
# Docker Desktop debe estar configurado para iniciar al ingresar al sistema.

set -eu

PROJECT_DIR="/Users/erick/vetcare/vetcare 2"
DOCKER_BIN="/usr/local/bin/docker"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/vetcare-start.log"
MAX_ATTEMPTS=30

mkdir -p "$LOG_DIR"
exec >> "$LOG_FILE" 2>&1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Inicio de tarea de arranque"

if [ ! -x "$DOCKER_BIN" ]; then
  echo "Docker no se encontró en $DOCKER_BIN"
  exit 1
fi

attempt=1
while ! "$DOCKER_BIN" info >/dev/null 2>&1; do
  if [ "$attempt" -ge "$MAX_ATTEMPTS" ]; then
    echo "Docker no estuvo disponible después de $MAX_ATTEMPTS intentos."
    exit 1
  fi
  echo "Docker aún no está disponible; esperando 10 segundos (intento $attempt/$MAX_ATTEMPTS)."
  attempt=$((attempt + 1))
  sleep 10
done

cd "$PROJECT_DIR"
"$DOCKER_BIN" compose up -d --remove-orphans
"$DOCKER_BIN" compose ps
echo "[$(date '+%Y-%m-%d %H:%M:%S')] VetCare levantado correctamente"
