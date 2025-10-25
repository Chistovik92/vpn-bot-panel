#!/bin/bash

set -e

echo "🔄 Создание резервной копии VPN Bot Panel..."

# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}ℹ️ $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️ $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

BACKUP_DIR="/opt/vpn-bot-panel/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/backup_$DATE.tar.gz"

# Создаем директорию для бэкапов
mkdir -p $BACKUP_DIR

log_info "Создание резервной копии в $BACKUP_FILE"

# Создаем бэкап
tar -czf $BACKUP_FILE \
    --exclude='venv' \
    --exclude='*.log' \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    /opt/vpn-bot-panel/

# Проверяем успешность
if [ $? -eq 0 ]; then
    log_success "Резервная копия создана: $BACKUP_FILE"
else
    log_error "Ошибка при создании резервной копии"
    exit 1
fi

# Удаляем старые бэкапы (храним последние 7)
log_info "Удаление старых бэкапов (старше 7 дней)..."
find $BACKUP_DIR -name "backup_*.tar.gz" -type f -mtime +7 -delete
log_success "Очистка старых бэкапов завершена"