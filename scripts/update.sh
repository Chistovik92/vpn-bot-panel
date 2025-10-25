#!/bin/bash

set -e

echo "🔄 Запуск обновления VPN Bot Panel..."

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

check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_success "Проверка прав: root"
    else
        log_error "Требуются права root"
        log_info "Запустите: sudo $0"
        exit 1
    fi
}

backup_system() {
    log_info "Создание резервной копии..."
    
    BACKUP_DIR="/opt/vpn-bot-panel/backups"
    DATE=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE="$BACKUP_DIR/backup_update_$DATE.tar.gz"
    
    mkdir -p $BACKUP_DIR
    
    tar -czf $BACKUP_FILE \
        --exclude='venv' \
        --exclude='*.log' \
        --exclude='*.pyc' \
        --exclude='__pycache__' \
        /opt/vpn-bot-panel/
    
    log_success "Резервная копия создана: $BACKUP_FILE"
}

stop_service() {
    log_info "Остановка сервиса..."
    
    if systemctl is-active --quiet vpn-bot-panel; then
        systemctl stop vpn-bot-panel
        log_success "Сервис остановлен"
    else
        log_warning "Сервис не запущен"
    fi
}

update_code() {
    log_info "Обновление кода..."
    
    cd /opt/vpn-bot-panel
    
    # Сохраняем текущую конфигурацию
    cp config.ini config.ini.backup
    
    # Получаем последние изменения (если используется git)
    if [ -d ".git" ]; then
        git pull origin main
    else
        log_warning "Git не инициализирован, обновление вручную"
    fi
    
    # Восстанавливаем конфигурацию
    cp config.ini.backup config.ini
    
    log_success "Код обновлен"
}

update_dependencies() {
    log_info "Обновление зависимостей..."
    
    cd /opt/vpn-bot-panel
    source venv/bin/activate
    
    pip install --upgrade pip
    pip install -r requirements.txt
    
    log_success "Зависимости обновлены"
}

update_database() {
    log_info "Обновление структуры базы данных..."
    
    cd /opt/vpn-bot-panel
    source venv/bin/activate
    
    python3 -c "
from app.database import Database
db = Database()
db.init_db()
print('✅ База данных обновлена')
"
}

start_service() {
    log_info "Запуск сервиса..."
    
    systemctl start vpn-bot-panel
    sleep 3
    
    if systemctl is-active --quiet vpn-bot-panel; then
        log_success "Сервис запущен"
    else
        log_error "Ошибка запуска сервиса"
        systemctl status vpn-bot-panel --no-pager
        exit 1
    fi
}

show_status() {
    log_info "Проверка статуса..."
    
    systemctl status vpn-bot-panel --no-pager
    
    log_success "Обновление завершено!"
    log_info "Логи: journalctl -u vpn-bot-panel -f"
}

main() {
    log_info "Начало процесса обновления..."
    
    check_root
    backup_system
    stop_service
    update_code
    update_dependencies
    update_database
    start_service
    show_status
}

main "$@"