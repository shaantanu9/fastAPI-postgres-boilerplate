#!/bin/bash
set -euo pipefail

# FastAPI PostgreSQL Backup Script
# Automated database backup with rotation and monitoring

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
DATABASE_URL="${DATABASE_URL:-}"
BACKUP_COMPRESSION="${BACKUP_COMPRESSION:-gzip}"
NOTIFICATION_WEBHOOK="${NOTIFICATION_WEBHOOK:-}"
MAX_BACKUP_SIZE="${MAX_BACKUP_SIZE:-10G}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Logging functions
log_info() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] INFO:${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARN:${NC} $1"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
}

# Validate environment
validate_environment() {
    log_info "Validating backup environment..."
    
    # Check if DATABASE_URL is set
    if [[ -z "$DATABASE_URL" ]]; then
        log_error "DATABASE_URL environment variable is not set"
        exit 1
    fi
    
    # Check if pg_dump is available
    if ! command -v pg_dump &> /dev/null; then
        log_error "pg_dump is not installed or not in PATH"
        exit 1
    fi
    
    # Create backup directory if it doesn't exist
    if [[ ! -d "$BACKUP_DIR" ]]; then
        mkdir -p "$BACKUP_DIR"
        log_info "Created backup directory: $BACKUP_DIR"
    fi
    
    # Check backup directory permissions
    if [[ ! -w "$BACKUP_DIR" ]]; then
        log_error "No write permission for backup directory: $BACKUP_DIR"
        exit 1
    fi
    
    # Check available disk space
    local available_space=$(df "$BACKUP_DIR" | awk 'NR==2 {print $4}')
    local required_space=1048576  # 1GB in KB
    
    if [[ $available_space -lt $required_space ]]; then
        log_warn "Low disk space. Available: ${available_space}KB, Recommended: ${required_space}KB"
    fi
    
    log_info "Environment validation completed"
}

# Send notification
send_notification() {
    local message="$1"
    local status="$2"  # success, warning, error
    
    if [[ -n "$NOTIFICATION_WEBHOOK" ]]; then
        curl -X POST "$NOTIFICATION_WEBHOOK" \
            -H "Content-Type: application/json" \
            -d "{\"text\":\"🗄️ Database Backup [$status]: $message\"}" \
            >/dev/null 2>&1 || log_warn "Failed to send notification"
    fi
    
    # Also log to syslog if available
    if command -v logger &> /dev/null; then
        logger -t "db-backup" "$status: $message"
    fi
}

# Parse DATABASE_URL
parse_database_url() {
    log_info "Parsing database connection details..."
    
    # Extract components from DATABASE_URL
    # Format: postgresql://user:password@host:port/database
    local url_pattern="postgresql://([^:]+):([^@]+)@([^:]+):([0-9]+)/(.+)"
    
    if [[ $DATABASE_URL =~ $url_pattern ]]; then
        DB_USER="${BASH_REMATCH[1]}"
        DB_PASSWORD="${BASH_REMATCH[2]}"
        DB_HOST="${BASH_REMATCH[3]}"
        DB_PORT="${BASH_REMATCH[4]}"
        DB_NAME="${BASH_REMATCH[5]}"
        
        log_info "Database: $DB_NAME on $DB_HOST:$DB_PORT"
    else
        log_error "Invalid DATABASE_URL format. Expected: postgresql://user:password@host:port/database"
        exit 1
    fi
}

# Test database connection
test_connection() {
    log_info "Testing database connection..."
    
    export PGPASSWORD="$DB_PASSWORD"
    
    if pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1; then
        log_info "Database connection successful"
    else
        log_error "Cannot connect to database"
        send_notification "Database connection failed" "error"
        exit 1
    fi
}

# Create backup
create_backup() {
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local backup_filename="backup_${DB_NAME}_${timestamp}.sql"
    local backup_path="$BACKUP_DIR/$backup_filename"
    
    log_info "Starting backup: $backup_filename"
    
    export PGPASSWORD="$DB_PASSWORD"
    
    # Start backup with progress monitoring
    {
        pg_dump \
            --host="$DB_HOST" \
            --port="$DB_PORT" \
            --username="$DB_USER" \
            --dbname="$DB_NAME" \
            --no-password \
            --verbose \
            --clean \
            --if-exists \
            --create \
            --format=plain \
            --no-owner \
            --no-privileges \
            > "$backup_path"
    } 2>&1 | while read -r line; do
        echo "[pg_dump] $line"
    done
    
    # Check if backup was successful
    if [[ ${PIPESTATUS[0]} -eq 0 && -f "$backup_path" ]]; then
        local backup_size=$(du -h "$backup_path" | cut -f1)
        log_info "Backup completed successfully: $backup_filename ($backup_size)"
        
        # Compress backup if requested
        if [[ "$BACKUP_COMPRESSION" == "gzip" ]]; then
            log_info "Compressing backup..."
            gzip "$backup_path"
            backup_path="${backup_path}.gz"
            backup_filename="${backup_filename}.gz"
            local compressed_size=$(du -h "$backup_path" | cut -f1)
            log_info "Backup compressed: $backup_filename ($compressed_size)"
        fi
        
        # Validate backup size
        local backup_size_bytes=$(stat -f%z "$backup_path" 2>/dev/null || stat -c%s "$backup_path")
        if [[ $backup_size_bytes -lt 1024 ]]; then
            log_error "Backup file is suspiciously small: $backup_size_bytes bytes"
            send_notification "Backup file too small: $backup_filename" "error"
            return 1
        fi
        
        # Test backup integrity (if compressed, test compression)
        if [[ "$backup_path" == *.gz ]]; then
            if ! gzip -t "$backup_path"; then
                log_error "Backup compression integrity check failed"
                send_notification "Backup corruption detected: $backup_filename" "error"
                return 1
            fi
        fi
        
        send_notification "Backup completed: $backup_filename ($backup_size)" "success"
        echo "$backup_path"  # Return backup path for further processing
        
    else
        log_error "Backup failed"
        send_notification "Backup failed for database: $DB_NAME" "error"
        return 1
    fi
}

# Clean old backups
cleanup_old_backups() {
    log_info "Cleaning up backups older than $RETENTION_DAYS days..."
    
    local deleted_count=0
    local total_space_freed=0
    
    # Find and delete old backup files
    while IFS= read -r -d '' file; do
        if [[ -f "$file" ]]; then
            local file_size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file")
            rm "$file"
            ((deleted_count++))
            ((total_space_freed += file_size))
            log_info "Deleted old backup: $(basename "$file")"
        fi
    done < <(find "$BACKUP_DIR" -name "backup_*.sql*" -type f -mtime +$RETENTION_DAYS -print0 2>/dev/null)
    
    if [[ $deleted_count -gt 0 ]]; then
        local space_freed_mb=$((total_space_freed / 1024 / 1024))
        log_info "Cleanup completed: $deleted_count files deleted, ${space_freed_mb}MB freed"
        send_notification "Cleanup: $deleted_count old backups deleted (${space_freed_mb}MB freed)" "success"
    else
        log_info "No old backups to clean up"
    fi
}

# Backup verification (optional)
verify_backup() {
    local backup_path="$1"
    
    if [[ -z "$backup_path" || ! -f "$backup_path" ]]; then
        log_error "Backup file not found for verification: $backup_path"
        return 1
    fi
    
    log_info "Verifying backup integrity..."
    
    # Basic checks
    local line_count
    if [[ "$backup_path" == *.gz ]]; then
        line_count=$(zcat "$backup_path" | wc -l)
    else
        line_count=$(wc -l < "$backup_path")
    fi
    
    if [[ $line_count -lt 10 ]]; then
        log_error "Backup verification failed: too few lines ($line_count)"
        return 1
    fi
    
    # Check for SQL structure
    local has_sql_structure=false
    if [[ "$backup_path" == *.gz ]]; then
        if zcat "$backup_path" | head -100 | grep -q "CREATE\|INSERT\|COPY"; then
            has_sql_structure=true
        fi
    else
        if head -100 "$backup_path" | grep -q "CREATE\|INSERT\|COPY"; then
            has_sql_structure=true
        fi
    fi
    
    if [[ "$has_sql_structure" == true ]]; then
        log_info "Backup verification passed: $line_count lines, SQL structure detected"
        return 0
    else
        log_error "Backup verification failed: no SQL structure detected"
        return 1
    fi
}

# Upload to cloud storage (optional)
upload_to_cloud() {
    local backup_path="$1"
    
    # AWS S3 upload
    if [[ -n "${AWS_S3_BUCKET:-}" ]] && command -v aws &> /dev/null; then
        log_info "Uploading backup to S3..."
        local s3_path="s3://${AWS_S3_BUCKET}/database-backups/$(basename "$backup_path")"
        
        if aws s3 cp "$backup_path" "$s3_path"; then
            log_info "Backup uploaded to S3: $s3_path"
            send_notification "Backup uploaded to cloud: $(basename "$backup_path")" "success"
        else
            log_error "Failed to upload backup to S3"
            send_notification "Cloud upload failed: $(basename "$backup_path")" "error"
        fi
    fi
    
    # Add other cloud providers here (Google Cloud, Azure, etc.)
}

# Generate backup report
generate_report() {
    log_info "Generating backup report..."
    
    local report_file="$BACKUP_DIR/backup_report_$(date '+%Y%m%d').json"
    local backup_count=$(find "$BACKUP_DIR" -name "backup_*.sql*" -type f | wc -l)
    local total_size=$(du -sb "$BACKUP_DIR" | cut -f1)
    local oldest_backup=$(find "$BACKUP_DIR" -name "backup_*.sql*" -type f -printf '%T+ %p\n' 2>/dev/null | sort | head -1 | cut -d' ' -f2-)
    local newest_backup=$(find "$BACKUP_DIR" -name "backup_*.sql*" -type f -printf '%T+ %p\n' 2>/dev/null | sort | tail -1 | cut -d' ' -f2-)
    
    cat > "$report_file" <<EOF
{
    "timestamp": "$(date -u '+%Y-%m-%dT%H:%M:%SZ')",
    "database": "$DB_NAME",
    "backup_directory": "$BACKUP_DIR",
    "total_backups": $backup_count,
    "total_size_bytes": $total_size,
    "total_size_human": "$(du -sh "$BACKUP_DIR" | cut -f1)",
    "oldest_backup": "$(basename "$oldest_backup" 2>/dev/null || echo "none")",
    "newest_backup": "$(basename "$newest_backup" 2>/dev/null || echo "none")",
    "retention_days": $RETENTION_DAYS,
    "last_cleanup": "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
}
EOF
    
    log_info "Backup report generated: $report_file"
}

# Main backup function
main() {
    local start_time=$(date '+%s')
    
    log_info "=== FastAPI Database Backup Started ==="
    log_info "Backup directory: $BACKUP_DIR"
    log_info "Retention period: $RETENTION_DAYS days"
    
    # Validate environment and parse DATABASE_URL
    validate_environment
    parse_database_url
    test_connection
    
    # Create backup
    local backup_path
    if backup_path=$(create_backup); then
        # Verify backup
        if verify_backup "$backup_path"; then
            log_info "Backup verification passed"
            
            # Upload to cloud if configured
            upload_to_cloud "$backup_path"
        else
            log_warn "Backup verification failed, but backup was created"
        fi
    else
        log_error "Backup creation failed"
        exit 1
    fi
    
    # Clean up old backups
    cleanup_old_backups
    
    # Generate report
    generate_report
    
    local end_time=$(date '+%s')
    local duration=$((end_time - start_time))
    
    log_info "=== Backup Completed in ${duration}s ==="
    send_notification "Database backup cycle completed in ${duration}s" "success"
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "FastAPI Database Backup Script"
        echo ""
        echo "Usage: $0 [options]"
        echo ""
        echo "Environment Variables:"
        echo "  DATABASE_URL         PostgreSQL connection URL (required)"
        echo "  BACKUP_DIR          Backup directory (default: /backups)"
        echo "  RETENTION_DAYS      Days to keep backups (default: 30)"
        echo "  BACKUP_COMPRESSION  gzip or none (default: gzip)"
        echo "  NOTIFICATION_WEBHOOK Webhook URL for notifications"
        echo "  AWS_S3_BUCKET       S3 bucket for cloud backup"
        echo ""
        echo "Examples:"
        echo "  $0                           # Run backup with defaults"
        echo "  RETENTION_DAYS=7 $0          # Keep backups for 7 days"
        echo "  BACKUP_COMPRESSION=none $0   # Don't compress backups"
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac 