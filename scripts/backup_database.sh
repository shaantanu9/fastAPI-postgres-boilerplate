#!/bin/bash
# Production Database Backup Script
# Runs daily at 2 AM via cron

set -e

# Configuration
BACKUP_DIR="/app/backups"
DB_URL="${DATABASE_URL}"
RETENTION_DAYS=30
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Perform compressed backup
BACKUP_FILE="$BACKUP_DIR/backup_$DATE.sql.gz"
echo "Starting backup: $BACKUP_FILE"

pg_dump "$DB_URL" | gzip > "$BACKUP_FILE"

# Verify backup
if gunzip -t "$BACKUP_FILE"; then
    echo "✅ Backup verified: $BACKUP_FILE"
    
    # Get backup size
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "Backup size: $BACKUP_SIZE"
    
    # Cleanup old backups
    find "$BACKUP_DIR" -name "backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete
    echo "Cleaned up backups older than $RETENTION_DAYS days"
    
    # Optional: Send success notification
    if [ ! -z "$BACKUP_WEBHOOK_URL" ]; then
        curl -X POST "$BACKUP_WEBHOOK_URL" \
             -H "Content-Type: application/json" \
             -d "{\"text\":\"✅ Database backup successful: $BACKUP_FILE ($BACKUP_SIZE)\"}" \
             --connect-timeout 5 --max-time 10 || true
    fi
    
else
    echo "❌ Backup verification failed!"
    
    # Optional: Send failure notification
    if [ ! -z "$BACKUP_WEBHOOK_URL" ]; then
        curl -X POST "$BACKUP_WEBHOOK_URL" \
             -H "Content-Type: application/json" \
             -d "{\"text\":\"❌ Database backup failed: $BACKUP_FILE\"}" \
             --connect-timeout 5 --max-time 10 || true
    fi
    
    exit 1
fi

echo "Backup completed successfully"
