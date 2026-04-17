#!/bin/bash
# ============================================
# start.sh — Levanta DB + Backend + Frontend
# ============================================
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
PIDS=()

# Agregar PostgreSQL al PATH si existe en la ubicación estándar
for pgdir in "/c/Program Files/PostgreSQL"/*/bin; do
    [ -d "$pgdir" ] && export PATH="$pgdir:$PATH" && break
done

cleanup() {
    echo ""
    echo "Deteniendo servicios..."
    for pid in "${PIDS[@]}"; do
        kill "$pid" 2>/dev/null || true
    done
    exit 0
}
trap cleanup SIGINT SIGTERM

# ---------- Colores ----------
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC}  $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ============================================
# 1. PostgreSQL — verificar que esté corriendo
# ============================================
info "Verificando PostgreSQL..."
if command -v pg_isready &>/dev/null; then
    if pg_isready -q -h localhost -p 5432; then
        info "PostgreSQL esta corriendo."
    else
        error "PostgreSQL no responde en localhost:5432."
        error "Asegurate de que el servicio este iniciado."
        exit 1
    fi
else
    warn "pg_isready no encontrado, asumiendo que PostgreSQL esta corriendo."
fi

# ============================================
# 2. Crear DB y ejecutar esquema si es necesario
# ============================================
DB_NAME="asistente_academico"
DB_USER="postgres"
DB_PASS="admin"
DB_HOST="localhost"
DB_PORT="5432"

export PGPASSWORD="$DB_PASS"
export PGCLIENTENCODING=UTF8

if command -v psql &>/dev/null; then
    # Crear la base si no existe
    DB_EXISTS=$(psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -tAc \
        "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" 2>/dev/null || echo "")

    if [ "$DB_EXISTS" != "1" ]; then
        info "Creando base de datos '$DB_NAME'..."
        psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -c "CREATE DATABASE $DB_NAME ENCODING 'UTF8';" 2>/dev/null
        info "Ejecutando esquema (01_schema.sql)..."
        psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -d "$DB_NAME" -f "$ROOT/db/01_schema.sql"
        if [ -f "$ROOT/db/02_seed.sql" ]; then
            info "Ejecutando seed (02_seed.sql)..."
            psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -d "$DB_NAME" -f "$ROOT/db/02_seed.sql"
        fi
        info "Base de datos lista."
    else
        info "Base de datos '$DB_NAME' ya existe."
    fi
else
    warn "psql no encontrado. Asegurate de que la DB '$DB_NAME' ya exista."
fi

unset PGPASSWORD

# ============================================
# 3. Backend — FastAPI + Uvicorn
# ============================================
info "Iniciando backend (FastAPI)..."

# Activar venv si existe
if [ -f "$ROOT/venv/Scripts/activate" ]; then
    source "$ROOT/venv/Scripts/activate"
elif [ -f "$ROOT/.venv/Scripts/activate" ]; then
    source "$ROOT/.venv/Scripts/activate"
elif [ -f "$ROOT/venv/bin/activate" ]; then
    source "$ROOT/venv/bin/activate"
elif [ -f "$ROOT/.venv/bin/activate" ]; then
    source "$ROOT/.venv/bin/activate"
fi

cd "$ROOT"
uvicorn app.main:app --reload --port 8000 &
PIDS+=($!)
info "Backend corriendo en http://localhost:8000"

# ============================================
# 4. Frontend — Vite dev server
# ============================================
info "Iniciando frontend (Vite)..."
cd "$ROOT/frontend"
npm run dev &
PIDS+=($!)
info "Frontend corriendo (ver puerto en la salida de Vite)"

# ============================================
# Esperar
# ============================================
echo ""
info "Todos los servicios iniciados. Ctrl+C para detener."
wait
