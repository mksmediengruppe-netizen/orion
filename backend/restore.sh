#!/bin/bash
# Использование: ./restore.sh 20260316_0300
DATE=$1
BACKUP_DIR="/var/www/orion/backend/data/backups"

if [ -z "$DATE" ]; then
    echo "Доступные бэкапы:"
    ls -la $BACKUP_DIR/db_*.db | tail -10
    echo ""
    echo "Использование: ./restore.sh 20260316_0300"
    exit 1
fi

echo "Восстанавливаю из бэкапа $DATE..."
systemctl stop orion-api

cp "$BACKUP_DIR/db_$DATE.db" /var/www/orion/backend/data/database.db
tar -xzf "$BACKUP_DIR/qdrant_$DATE.tar.gz" -C /var/www/orion/backend/data/ 2>/dev/null
tar -xzf "$BACKUP_DIR/memory_$DATE.tar.gz" -C /var/www/orion/backend/data/ 2>/dev/null

systemctl start orion-api
echo "Готово. Проверь: curl http://127.0.0.1:3510/api/health"
