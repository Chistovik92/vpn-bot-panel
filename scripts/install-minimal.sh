#!/bin/bash

set -e

echo "🚀 Запуск минимальной установки VPN Bot Panel..."

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

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
INSTALL_DIR="/opt/vpn-bot-panel"

cd "$PROJECT_ROOT"

check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_success "Проверка прав: root"
    else
        log_error "Требуются права root"
        log_info "Запустите: sudo $0"
        exit 1
    fi
}

check_disk_space() {
    log_info "Проверка свободного места..."
    
    local available_kb=$(df / | awk 'NR==2 {print $4}')
    local available_mb=$((available_kb / 1024))
    local min_space_mb=200  # Минимум 200MB для минимальной установки
    
    if [ "$available_mb" -lt "$min_space_mb" ]; then
        log_error "Недостаточно свободного места!"
        log_info "Доступно: ${available_mb} MB"
        log_info "Требуется: ${min_space_mb} MB"
        exit 1
    else
        log_success "Свободного места достаточно: ${available_mb} MB"
    fi
}

install_absolute_minimum() {
    log_info "Установка абсолютного минимума пакетов..."
    
    # Очищаем кэш
    apt clean 2>/dev/null || true
    
    if command -v apt &>/dev/null; then
        # Обновляем только индексы (без загрузки пакетов)
        apt update -o Acquire::Check-Valid-Until=false -o Acquire::Check-Date=false
        
        # Устанавливаем только Python и SQLite
        apt install -y --no-install-recommends \
            python3 \
            python3-venv \
            sqlite3
        
        log_success "Базовые пакеты установлены"
    else
        log_error "Не удалось установить пакеты"
        exit 1
    fi
}

setup_minimal_installation() {
    log_info "Настройка минимальной установки..."
    
    mkdir -p "$INSTALL_DIR"
    cd "$INSTALL_DIR"
    
    # Копируем только самое необходимое
    cp -r "$PROJECT_ROOT/app" .
    cp "$PROJECT_ROOT/requirements.txt" .
    cp "$PROJECT_ROOT/run.py" .
    
    # Создаем минимальный config.ini
    cat > config.ini << EOF
[DATABASE]
path = data/vpn_bot.db
backup_path = backups/

[BOT]
token = YOUR_BOT_TOKEN_HERE
admin_telegram_id = YOUR_ADMIN_ID

[WEB]
secret_key = $(python3 -c "import os; print(os.urandom(24).hex())")
host = 127.0.0.1
port = 5000
debug = False

[SECURITY]
auto_unban_interval_hours = 6
max_login_attempts = 5
session_timeout_minutes = 60
backup_retention_days = 7

[LOGGING]
level = INFO
file = logs/vpn_bot.log
max_size_mb = 10
backup_count = 5
EOF
    
    # Создаем директории
    mkdir -p data logs backups
    
    # Настраиваем venv
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    
    # Инициализируем базу данных
    python3 -c "import sys; sys.path.append('.'); from app.database import Database; db = Database(); db.init_db()"
    
    log_success "Минимальная установка завершена"
}

show_minimal_instructions() {
    echo ""
    log_success "🎉 Минимальная установка завершена!"
    echo ""
    log_info "📋 Следующие шаги:"
    echo "  1. Отредактируйте config.ini:"
    echo "     sudo nano $INSTALL_DIR/config.ini"
    echo ""
    echo "  2. Установите токен бота и ID администратора"
    echo ""
    echo "  3. Запустите бота вручную:"
    echo "     cd $INSTALL_DIR && source venv/bin/activate && python3 run.py"
    echo ""
    echo "  4. Для запуска как сервиса выполните полную установку позже:"
    echo "     sudo ./scripts/install.sh"
    echo ""
}

main() {
    log_info "Минимальная установка VPN Bot Panel"
    log_info "Эта установка использует минимум места и функциональности"
    
    check_root
    check_disk_space
    install_absolute_minimum
    setup_minimal_installation
    show_minimal_instructions
}

main "$@"