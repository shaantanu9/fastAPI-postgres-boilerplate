#!/bin/bash

set -e

# Load .env variables
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
else
  echo ".env file not found!"
  exit 1
fi

# Ensure DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
  echo "DATABASE_URL is not set in .env!"
  exit 1
fi

# Convert async URL to sync for Alembic
SYNC_DB_URL="$DATABASE_URL"
if [[ "$DATABASE_URL" == postgresql+asyncpg* ]]; then
  SYNC_DB_URL="${DATABASE_URL/+asyncpg/}"
fi

# Patch alembic.ini sqlalchemy.url
if grep -q "^sqlalchemy.url" alembic.ini; then
  sed -i.bak "s|^sqlalchemy.url.*|sqlalchemy.url = $SYNC_DB_URL|" alembic.ini
else
  echo "sqlalchemy.url = $SYNC_DB_URL" >> alembic.ini
fi

echo "alembic.ini sqlalchemy.url set to: $SYNC_DB_URL"

# Run Alembic migration command
alembic upgrade head