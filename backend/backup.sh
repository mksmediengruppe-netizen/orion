#!/bin/bash
BACKUP_DIR="/var/www/orion/backend/data/backups"
DATE=$(date +%Y%m%d_%H%M)
mkdir -p $BACKUP_DIR

# База данных
cp /var/www/orion/backend/data/database.db "$BACKUP_DIR/db_$DATE.db" 2>/dev/null

# Qdrant (векторная память)
tar -czf "$BACKUP_DIR/qdrant_$DATE.tar.gz" -C /var/www/orion/backend/data qdrant_storage 2>/dev/null

# Memory v9 данные
tar -czf "$BACKUP_DIR/memory_$DATE.tar.gz" -C /var/www/orion/backend/data memory 2>/dev/null

# Конфиги
tar -czf "$BACKUP_DIR/config_$DATE.tar.gz" \
    /var/www/orion/backend/.env \
    /etc/nginx/sites-enabled/orion.conf \
    /etc/systemd/system/orion-api.service \
    2>/dev/null

# Чистка старых бэкапов (старше 30 дней)
find $BACKUP_DIR -mtime +30 -delete 2>/dev/null

echo "[$(date)] Backup completed: $BACKUP_DIR/*_$DATE.*" >> /var/log/orion-backup.log
