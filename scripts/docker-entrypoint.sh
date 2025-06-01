#!/bin/bash
# Docker Entrypoint Script for FastAPI SaaS Application

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

# Wait for database to be ready
wait_for_db() {
    log "Waiting for database to be ready..."
    
    # Extract database connection details from DATABASE_URL
    if [ -n "$DATABASE_URL" ]; then
        # Parse DATABASE_URL (format: postgresql://user:pass@host:port/db)
        DB_URL=${DATABASE_URL#*://}
        DB_CREDS=${DB_URL%@*}
        DB_HOST_PORT=${DB_URL#*@}
        DB_HOST=${DB_HOST_PORT%/*}
        DB_NAME=${DB_HOST_PORT#*/}
        
        # Remove any query parameters
        DB_NAME=${DB_NAME%\?*}
        
        # Extract host and port
        if [[ $DB_HOST == *:* ]]; then
            DB_PORT=${DB_HOST#*:}
            DB_HOST=${DB_HOST%:*}
        else
            DB_PORT=5432
        fi
        
        # Extract username and password
        DB_USER=${DB_CREDS%:*}
        DB_PASS=${DB_CREDS#*:}
        
        log "Database: $DB_HOST:$DB_PORT/$DB_NAME"
        
        # Wait for database
        for i in {1..30}; do
            if PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1" > /dev/null 2>&1; then
                log "Database is ready!"
                break
            else
                if [ $i -eq 30 ]; then
                    error "Database is not ready after 30 attempts"
                    exit 1
                fi
                warn "Database not ready, waiting... (attempt $i/30)"
                sleep 2
            fi
        done
    else
        warn "DATABASE_URL not set, skipping database check"
    fi
}

# Wait for Redis to be ready
wait_for_redis() {
    if [ -n "$REDIS_URL" ]; then
        log "Waiting for Redis to be ready..."
        
        # Extract Redis connection details
        REDIS_HOST_PORT=${REDIS_URL#redis://}
        REDIS_HOST_PORT=${REDIS_HOST_PORT%/*}
        
        if [[ $REDIS_HOST_PORT == *:* ]]; then
            REDIS_HOST=${REDIS_HOST_PORT%:*}
            REDIS_PORT=${REDIS_HOST_PORT#*:}
        else
            REDIS_HOST=$REDIS_HOST_PORT
            REDIS_PORT=6379
        fi
        
        log "Redis: $REDIS_HOST:$REDIS_PORT"
        
        # Wait for Redis
        for i in {1..30}; do
            if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping > /dev/null 2>&1; then
                log "Redis is ready!"
                break
            else
                if [ $i -eq 30 ]; then
                    error "Redis is not ready after 30 attempts"
                    exit 1
                fi
                warn "Redis not ready, waiting... (attempt $i/30)"
                sleep 2
            fi
        done
    else
        warn "REDIS_URL not set, skipping Redis check"
    fi
}

# Run database migrations
run_migrations() {
    log "Running database migrations..."
    
    if command -v alembic >/dev/null 2>&1; then
        # Check if migrations directory exists
        if [ -d "alembic" ] || [ -d "migrations" ]; then
            alembic upgrade head
            log "Database migrations completed"
        else
            warn "No migrations directory found, skipping migrations"
        fi
    else
        warn "Alembic not found, skipping migrations"
    fi
}

# Initialize application data
init_app_data() {
    log "Initializing application data..."
    
    # Run RBAC seeding if in production and first run
    if [ "$ENVIRONMENT" = "production" ] && [ "$SEED_DATA" = "true" ]; then
        log "Seeding RBAC data..."
        python -c "
import asyncio
from app.scripts.seed_rbac import seed_rbac
try:
    asyncio.run(seed_rbac())
    print('RBAC data seeded successfully')
except Exception as e:
    print(f'RBAC seeding failed: {e}')
"
    fi
}

# Health check function
health_check() {
    log "Performing health check..."
    
    # Check if the application responds
    for i in {1..10}; do
        if curl -f http://localhost:8000/api/v1/health/ready >/dev/null 2>&1; then
            log "Application health check passed"
            return 0
        else
            if [ $i -eq 10 ]; then
                error "Application health check failed after 10 attempts"
                return 1
            fi
            warn "Health check failed, retrying... (attempt $i/10)"
            sleep 3
        fi
    done
}

# Setup logging
setup_logging() {
    log "Setting up logging..."
    
    # Create log directories
    mkdir -p /app/logs
    
    # Set log levels based on environment
    if [ "$ENVIRONMENT" = "production" ]; then
        export LOG_LEVEL="INFO"
    elif [ "$ENVIRONMENT" = "development" ]; then
        export LOG_LEVEL="DEBUG"
    else
        export LOG_LEVEL="INFO"
    fi
    
    log "Log level set to: $LOG_LEVEL"
}

# Validate environment
validate_environment() {
    log "Validating environment variables..."
    
    # Required environment variables
    REQUIRED_VARS=(
        "DATABASE_URL"
        "JWT_SECRET_TOKEN"
        "ENVIRONMENT"
    )
    
    for var in "${REQUIRED_VARS[@]}"; do
        if [ -z "${!var}" ]; then
            error "Required environment variable $var is not set"
            exit 1
        fi
    done
    
    # Validate JWT secret length
    if [ ${#JWT_SECRET_TOKEN} -lt 32 ]; then
        error "JWT_SECRET_TOKEN must be at least 32 characters long"
        exit 1
    fi
    
    log "Environment validation passed"
}

# Main initialization
main() {
    log "Starting FastAPI SaaS Application..."
    log "Environment: ${ENVIRONMENT:-development}"
    
    # Validate environment
    validate_environment
    
    # Setup logging
    setup_logging
    
    # Wait for dependencies only if not in test mode
    if [ "$ENVIRONMENT" != "test" ]; then
        wait_for_db
        wait_for_redis
    fi
    
    # Run migrations
    if [ "$SKIP_MIGRATIONS" != "true" ]; then
        run_migrations
    fi
    
    # Initialize application data
    if [ "$SKIP_INIT_DATA" != "true" ]; then
        init_app_data
    fi
    
    log "Initialization completed successfully"
    
    # Execute the command passed to the container
    log "Starting command: $*"
    exec "$@"
}

# Handle special commands
case "${1}" in
    "health-check")
        health_check
        exit $?
        ;;
    "migrate")
        validate_environment
        wait_for_db
        run_migrations
        exit 0
        ;;
    "seed-data")
        validate_environment
        wait_for_db
        init_app_data
        exit 0
        ;;
    "worker")
        validate_environment
        wait_for_db
        wait_for_redis
        log "Starting Procrastinate worker..."
        exec python -m procrastinate worker --concurrency "${WORKER_CONCURRENCY:-4}"
        ;;
    "shell")
        validate_environment
        log "Starting interactive shell..."
        exec python -c "
import asyncio
from app.db.session import get_async_session
from app.services import *
print('FastAPI SaaS Shell - Database and services loaded')
print('Available: db session, all services')
"
        ;;
    *)
        main "$@"
        ;;
esac 