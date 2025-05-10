#!/bin/bash
# Simple setup script for FastAPI + PostgreSQL boilerplate
# Usage: bash setup.sh

set -e

# 1. Check for uv
if ! command -v uv &> /dev/null; then
    echo "[INFO] uv not found. Installing via pip..."
    pip install uv
fi

# 2. Create .env if not present
if [ ! -f .env ]; then
    echo "[INFO] Creating default .env file. Please edit DATABASE_URL before running!"
    echo "DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/postgres" > .env
else
    echo "[INFO] .env already exists."
fi

# 3. Install dependencies
uv sync

# 4. Run Alembic migrations (if alembic_migrate.sh is present)
if [ -f ./alembic_migrate.sh ]; then
    echo "[INFO] Running Alembic migrations using alembic_migrate.sh..."
    ./alembic_migrate.sh
else
    echo "[INFO] No alembic_migrate.sh found. You can run migrations manually:"
    echo "  1. Ensure .env uses sync DB URL (postgresql://...)"
    echo "  2. Ensure alembic.ini sqlalchemy.url is set to sync DB URL"
    echo "  3. Run: alembic upgrade head"
fi

# 5. Print success message
echo "[INFO] Setup complete! To run the server:"
echo "uv run -- uvicorn main:app --reload"
