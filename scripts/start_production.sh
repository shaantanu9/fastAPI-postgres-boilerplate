#!/bin/bash
# Production Startup Script for FastAPI SaaS Application

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

# Check if running as root (not recommended for production)
if [ "$EUID" -eq 0 ]; then
    warn "Running as root is not recommended for production"
    warn "Consider creating a dedicated user for the application"
fi

# Set production environment variables
export ENVIRONMENT=production
export LOG_LEVEL=info
export PYTHONPATH=/app:$PYTHONPATH

# Check if we're running locally (not in Docker/server)
if [ ! -d "/app" ] && [ "$(whoami)" != "fastapi" ]; then
    warn "Running locally - using current user instead of 'fastapi' user"
    export ENVIRONMENT=development  # This prevents user/group settings
fi

# Validate required environment variables
log "Validating environment variables..."
REQUIRED_VARS=(
    "DATABASE_URL"
    "JWT_SECRET_TOKEN"
)

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        error "Required environment variable $var is not set"
        error "Please set all required environment variables before running in production"
        exit 1
    fi
done

# Validate JWT secret length
if [ ${#JWT_SECRET_TOKEN} -lt 32 ]; then
    error "JWT_SECRET_TOKEN must be at least 32 characters long for security"
    exit 1
fi

log "Environment validation passed"

# Create necessary directories
log "Creating necessary directories..."
mkdir -p logs uploads tmp
chmod 755 logs uploads tmp

# Choose the right config based on environment
if [ "$ENVIRONMENT" = "development" ]; then
    CONFIG_FILE="scripts/setup/gunicorn.stable.conf.py"
    log "Using stable configuration for local development"
else
    CONFIG_FILE="scripts/setup/gunicorn.conf.py"
    log "Using production configuration"
fi

# Check if Gunicorn config exists
if [ ! -f "$CONFIG_FILE" ]; then
    error "Gunicorn configuration file not found: $CONFIG_FILE"
    exit 1
fi

# Display configuration info
log "Production Configuration:"
log "  Environment: $ENVIRONMENT"
log "  Log Level: $LOG_LEVEL"
log "  Config File: $CONFIG_FILE"
log "  Workers: ${GUNICORN_WORKERS:-auto}"
log "  Bind: ${GUNICORN_BIND:-127.0.0.1:8000}"

# Start the application
log "Starting FastAPI SaaS Application in Production Mode..."
log "Command: gunicorn --config $CONFIG_FILE app.main:app"

exec gunicorn --config "$CONFIG_FILE" app.main:app 