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

# 4. Run migrations (create tables)
echo "[INFO] Running FastAPI app to create tables..."
uv run -- python -c "from app import models; from app.database import engine; import asyncio; async def create(): import sys; try: async with engine.begin() as conn: await conn.run_sync(models.Base.metadata.create_all); print('[INFO] Tables created!') except Exception as e: print('[ERROR]', e); sys.exit(1); asyncio.run(create())"

# 5. Print success message
echo "[INFO] Setup complete! To run the server:"
echo "uv run -- uvicorn main:app --reload"
