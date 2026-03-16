#!/bin/bash
# ORION Digital — Watchdog Healthcheck
# Проверяет nginx, API, диск, RAM и перезапускает при проблемах
# Логирует в /var/log/orion-health.log
# Запускается каждые 2 минуты через crontab

LOG="/var/log/orion-health.log"
NGINX_URL="https://orion.mksitdev.ru"
API_URL="http://localhost:3510/api/health"
DISK_THRESHOLD=90
RAM_THRESHOLD=90
MAX_LOG_SIZE=10485760  # 10MB

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG"
}

# Ротация лога если > 10MB
if [ -f "$LOG" ] && [ $(stat -c%s "$LOG" 2>/dev/null || echo 0) -gt $MAX_LOG_SIZE ]; then
    mv "$LOG" "${LOG}.old"
    log "Log rotated"
fi

ERRORS=0

# ── 1. Проверка nginx ──────────────────────────────────────────
check_nginx() {
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$NGINX_URL" 2>/dev/null)
    if [[ "$HTTP_CODE" == "200" || "$HTTP_CODE" == "301" || "$HTTP_CODE" == "302" ]]; then
        log "[OK] nginx: HTTP $HTTP_CODE"
    else
        log "[WARN] nginx: HTTP $HTTP_CODE — перезапускаю"
        NGINX_CONTAINER=$(docker ps --filter name=nginx -q 2>/dev/null | head -1)
        if [ -n "$NGINX_CONTAINER" ]; then
            docker exec "$NGINX_CONTAINER" nginx -s reload 2>/dev/null && log "[OK] nginx reload OK" || log "[ERROR] nginx reload failed"
        else
            log "[ERROR] nginx container not found"
        fi
        ERRORS=$((ERRORS + 1))
    fi
}

# ── 2. Проверка API ────────────────────────────────────────────
check_api() {
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$API_URL" 2>/dev/null)
    if [[ "$HTTP_CODE" == "200" ]]; then
        log "[OK] API: HTTP $HTTP_CODE"
    else
        log "[WARN] API: HTTP $HTTP_CODE — перезапускаю orion-api"
        systemctl restart orion-api 2>/dev/null && log "[OK] orion-api restarted" || log "[ERROR] orion-api restart failed"
        sleep 5
        # Повторная проверка
        HTTP_CODE2=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$API_URL" 2>/dev/null)
        log "[INFO] API после перезапуска: HTTP $HTTP_CODE2"
        ERRORS=$((ERRORS + 1))
    fi
}

# ── 3. Проверка диска ──────────────────────────────────────────
check_disk() {
    DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | tr -d '%')
    if [ "$DISK_USAGE" -gt "$DISK_THRESHOLD" ]; then
        log "[WARN] Диск: ${DISK_USAGE}% использовано (порог ${DISK_THRESHOLD}%)"
        # Очистка старых логов и временных файлов
        find /var/log -name "*.gz" -mtime +7 -delete 2>/dev/null
        find /tmp -mtime +1 -delete 2>/dev/null
        journalctl --vacuum-size=100M 2>/dev/null
        log "[INFO] Очистка выполнена, диск: $(df / | awk 'NR==2 {print $5}')"
        ERRORS=$((ERRORS + 1))
    else
        log "[OK] Диск: ${DISK_USAGE}%"
    fi
}

# ── 4. Проверка RAM ────────────────────────────────────────────
check_ram() {
    RAM_USAGE=$(free | awk 'NR==2 {printf "%.0f", $3/$2*100}')
    if [ "$RAM_USAGE" -gt "$RAM_THRESHOLD" ]; then
        log "[WARN] RAM: ${RAM_USAGE}% использовано (порог ${RAM_THRESHOLD}%)"
        # Сбрасываем кэш
        sync && echo 3 > /proc/sys/vm/drop_caches 2>/dev/null
        log "[INFO] RAM кэш сброшен"
        ERRORS=$((ERRORS + 1))
    else
        log "[OK] RAM: ${RAM_USAGE}%"
    fi
}

# ── Запуск проверок ────────────────────────────────────────────
log "=== Healthcheck START ==="
check_nginx
check_api
check_disk
check_ram

if [ "$ERRORS" -eq 0 ]; then
    log "=== Healthcheck OK (все проверки пройдены) ==="
else
    log "=== Healthcheck DONE (обнаружено проблем: $ERRORS) ==="
fi
