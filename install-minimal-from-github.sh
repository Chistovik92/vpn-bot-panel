#!/bin/bash

set -e

echo "🚀 Автоматическая минимальная установка VPN Bot Panel с GitHub..."

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

# Конфигурация
REPO_URL="https://github.com/Chistovik92/vpn-bot-panel.git"
BRANCH="Dev_Bot-plan"
INSTALL_DIR="/opt/vpn-bot-panel"
TEMP_DIR="/tmp/vpn-bot-panel-minimal-install"

check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_success "Проверка прав: root"
    else
        log_error "Требуются права root"
        log_info "Запустите: sudo bash <(curl -sSL https://raw.githubusercontent.com/Chistovik92/vpn-bot-panel/Dev_Bot-plan/install-minimal-from-github.sh)"
        exit 1
    fi
}

check_disk_space() {
    log_info "Проверка свободного места на диске..."
    
    local available_kb=$(df / | awk 'NR==2 {print $4}')
    local available_mb=$((available_kb / 1024))
    local min_space_mb=100  # Всего 100MB для минимальной установки
    
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
    
    if command -v apt &>/dev/null; then
        # Минимальное обновление и установка
        apt update -o Acquire::Check-Valid-Until=false -o Acquire::Check-Date=false
        
        # Только Python и SQLite
        apt install -y --no-install-recommends \
            python3 \
            python3-venv \
            sqlite3 \
            curl
        
        log_success "Базовые пакеты установлены"
    else
        log_error "Не удалось установить базовые пакеты"
        exit 1
    fi
}

download_minimal_files() {
    log_info "Загрузка минимального набора файлов..."
    
    # Создаем временную директорию
    rm -rf "$TEMP_DIR"
    mkdir -p "$TEMP_DIR"
    
    # Скачиваем отдельные файлы через raw.githubusercontent.com
    local files=(
        "app/database.py"
        "app/config.py" 
        "app/bot.py"
        "app/xui_api.py"
        "app/payment.py"
        "requirements.txt"
        "run.py"
    )
    
    for file in "${files[@]}"; do
        local dir=$(dirname "$file")
        mkdir -p "$TEMP_DIR/$dir"
        
        if curl -sSL "https://raw.githubusercontent.com/Chistovik92/vpn-bot-panel/$BRANCH/$file" \
             -o "$TEMP_DIR/$file" 2>/dev/null; then
            log_info "✓ $file"
        else
            log_error "Ошибка загрузки: $file"
        fi
    done
    
    # Создаем базовую структуру app
    mkdir -p "$TEMP_DIR/app"
    touch "$TEMP_DIR/app/__init__.py"
    
    log_success "Минимальные файлы загружены"
}

setup_minimal_installation() {
    log_info "Настройка минимальной установки..."
    
    # Создаем директорию установки
    mkdir -p "$INSTALL_DIR"
    cd "$INSTALL_DIR"
    
    # Копируем файлы
    cp -r "$TEMP_DIR/app" .
    cp "$TEMP_DIR/requirements.txt" .
    cp "$TEMP_DIR/run.py" .
    
    # Создаем минимальный config.ini
    cat > config.ini << 'EOF'
[DATABASE]
path = data/vpn_bot.db
backup_path = backups/

[BOT]
token = YOUR_BOT_TOKEN_HERE
admin_telegram_id = YOUR_ADMIN_ID

[WEB]
secret_key = GENERATED_SECRET_KEY
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
    
    # Создаем необходимые директории
    mkdir -p data logs backups
    
    log_success "Минимальная структура создана"
}

setup_python_environment() {
    log_info "Настройка Python окружения..."
    
    cd "$INSTALL_DIR"
    
    # Создаем venv
    python3 -m venv venv
    source venv/bin/activate
    
    # Устанавливаем зависимости
    pip install --upgrade pip
    
    # Базовые зависимости (остальные можно установить позже)
    pip install python-telegram-bot flask requests cryptography
    
    log_success "Python окружение настроено"
}

initialize_database() {
    log_info "Инициализация базы данных..."
    
    cd "$INSTALL_DIR"
    source venv/bin/activate
    
    # Создаем минимальную инициализацию БД
    python3 -c "
import sys
import os
sys.path.append('.')

# Минимальная инициализация БД
import sqlite3
conn = sqlite3.connect('data/vpn_bot.db')
cursor = conn.cursor()

# Базовая таблица пользователей
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL,
        username TEXT,
        full_name TEXT,
        role TEXT DEFAULT 'user',
        balance REAL DEFAULT 0.0,
        registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_active BOOLEAN DEFAULT TRUE,
        is_banned BOOLEAN DEFAULT FALSE
    )
''')

# Базовая таблица серверов
cursor.execute('''
    CREATE TABLE IF NOT EXISTS servers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        url TEXT NOT NULL,
        username TEXT NOT NULL,
        password TEXT NOT NULL,
        location TEXT,
        is_active BOOLEAN DEFAULT TRUE
    )
''')

conn.commit()
conn.close()
print('✅ База данных инициализирована')
"
}

create_minimal_service() {
    log_info "Создание systemd сервиса..."
    
    local service_file="/etc/systemd/system/vpn-bot-panel.service"
    
    cat > "$service_file" << EOF
[Unit]
Description=VPN Bot Panel (Minimal)
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR
Environment=PYTHONPATH=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python3 run.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable vpn-bot-panel.service
    
    log_success "Systemd сервис создан"
}

cleanup_temp() {
    log_info "Очистка временных файлов..."
    rm -rf "$TEMP_DIR"
    log_success "Временные файлы удалены"
}

show_minimal_instructions() {
    echo ""
    log_success "🎉 Минимальная установка завершена!"
    echo ""
    log_info "📋 Следующие шаги:"
    echo "  1. Настройте конфигурацию:"
    echo "     sudo nano $INSTALL_DIR/config.ini"
    echo ""
    echo "  2. Установите токен бота и ID администратора:"
    echo "     token = YOUR_ACTUAL_BOT_TOKEN"
    echo "     admin_telegram_id = YOUR_TELEGRAM_ID"
    echo ""
    echo "  3. Запустите систему:"
    echo "     sudo systemctl start vpn-bot-panel"
    echo ""
    echo "  4. Или запустите вручную:"
    echo "     cd $INSTALL_DIR && source venv/bin/activate && python3 run.py"
    echo ""
    log_info "⚠️  Ограничения минимальной версии:"
    echo "     • Нет веб-панели"
    echo "     • Нет шаблонов и статических файлов"
    echo "     • Базовые функции бота"
    echo ""
    log_info "📖 Для полной функциональности выполните:"
    echo "     curl -sSL https://raw.githubusercontent.com/Chistovik92/vpn-bot-panel/Dev_Bot-plan/install-from-github.sh | sudo bash"
    echo ""
}

main() {
    log_info "Начало минимальной установки с GitHub..."
    log_info "Это займет меньше места и времени"
    
    check_root
    check_disk_space
    install_absolute_minimum
    download_minimal_files
    setup_minimal_installation
    setup_python_environment
    initialize_database
    create_minimal_service
    cleanup_temp
    show_minimal_instructions
}

main "$@"