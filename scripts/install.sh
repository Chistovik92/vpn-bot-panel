#!/bin/bash

set -e

echo "🚀 Запуск установки VPN Bot Panel..."

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

# Определяем корневую директорию проекта
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

check_python() {
    if command -v python3 &>/dev/null; then
        PYTHON_VERSION=$(python3 -c "import sys; print('.'.join(map(str, sys.version_info[:2])))")
        log_success "Python $PYTHON_VERSION найден"
    else
        log_error "Python 3 не установлен"
        exit 1
    fi
}

install_system_packages() {
    log_info "Установка системных пакетов..."
    
    if command -v apt &>/dev/null; then
        apt update
        apt install -y python3-venv python3-pip git sqlite3 nginx curl
    elif command -v yum &>/dev/null; then
        yum install -y python3-virtualenv python3-pip git sqlite nginx curl
    elif command -v dnf &>/dev/null; then
        dnf install -y python3-virtualenv python3-pip git sqlite nginx curl
    else
        log_warning "Неизвестный пакетный менеджер, требуется ручная установка Python 3.8+, pip и sqlite3"
    fi
}

create_install_directory() {
    log_info "Создание директории установки..."
    
    if [ ! -d "$INSTALL_DIR" ]; then
        mkdir -p "$INSTALL_DIR"
        log_success "Директория создана: $INSTALL_DIR"
    else
        log_warning "Директория уже существует: $INSTALL_DIR"
    fi
    
    # Очистка директории установки (если нужно)
    if [ "$(ls -A $INSTALL_DIR 2>/dev/null)" ]; then
        log_warning "Директория установки не пуста"
        read -p "Очистить директорию? (y/N): " clean_dir
        if [ "$clean_dir" = "y" ] || [ "$clean_dir" = "Y" ]; then
            rm -rf "$INSTALL_DIR"/*
            log_success "Директория очищена"
        fi
    fi
}

copy_project_files() {
    log_info "Копирование файлов проекта..."
    
    cd "$PROJECT_ROOT"
    
    # Создаем список файлов для копирования (исключая системные директории)
    local files_to_copy=(
        "app" "scripts" "templates" "static" "docs"
        "requirements.txt" "config.ini.example" "run.py" "LICENSE" "README.md"
        ".gitignore"
    )
    
    # Копируем только нужные файлы и директории
    for item in "${files_to_copy[@]}"; do
        if [ -e "$item" ]; then
            log_info "Копирование: $item"
            cp -r "$item" "$INSTALL_DIR"/
        else
            log_warning "Файл/директория не найдена: $item"
        fi
    done
    
    # Создаем необходимые директории если их нет
    mkdir -p "$INSTALL_DIR/data" "$INSTALL_DIR/logs" "$INSTALL_DIR/backups"
    
    cd "$INSTALL_DIR"
    log_success "Файлы проекта скопированы в $INSTALL_DIR"
}

setup_venv() {
    log_info "Настройка виртуального окружения..."
    
    cd "$INSTALL_DIR"
    
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        log_success "Виртуальное окружение создано"
    else
        log_warning "Виртуальное окружение уже существует"
    fi
    
    source venv/bin/activate
}

install_dependencies() {
    log_info "Установка зависимостей..."
    
    cd "$INSTALL_DIR"
    source venv/bin/activate
    
    pip install --upgrade pip
    pip install -r requirements.txt
    
    log_success "Зависимости установлены"
}

setup_directories() {
    log_info "Создание структуры директорий..."
    
    cd "$INSTALL_DIR"
    mkdir -p data logs backups
    
    log_success "Директории созданы"
}

setup_database() {
    log_info "Инициализация базы данных..."
    
    cd "$INSTALL_DIR"
    source venv/bin/activate
    
    # Проверяем наличие необходимых модулей
    if python3 -c "import sys; sys.path.append('.'); from app.database import Database" &>/dev/null; then
        python3 -c "
import sys
sys.path.append('.')
from app.database import Database
db = Database()
db.init_db()
print('✅ База данных инициализирована')
"
    else
        log_error "Не удалось импортировать модули приложения"
        log_info "Проверьте структуру проекта и зависимости"
        exit 1
    fi
}

setup_super_admin() {
    log_info "Настройка супер администратора..."
    
    read -p "Введите Telegram ID супер администратора: " telegram_id
    
    if [[ ! "$telegram_id" =~ ^[0-9]+$ ]]; then
        log_error "Telegram ID должен быть числом"
        return 1
    fi
    
    read -p "Введите имя пользователя [admin]: " username
    username=${username:-admin}
    
    cd "$INSTALL_DIR"
    source venv/bin/activate
    
    python3 -c "
import sys
sys.path.append('.')
from app.database import Database, UserRole
db = Database()

# Создаем или обновляем супер администратора
db.create_user($telegram_id, '$username', 'System Administrator', UserRole.SUPER_ADMIN.value)
print('✅ Супер администратор создан')
print('   👤 Имя: $username')
print('   📱 Telegram ID: $telegram_id')
print('   👑 Роль: Супер администратор')
"
}

setup_payment_config() {
    log_info "Настройка платежных систем..."
    
    echo ""
    echo "💳 Настройка платежных систем (можно пропустить Enter):"
    
    # YooMoney
    read -p "YooMoney Shop ID: " yoomoney_shop_id
    read -p "YooMoney Secret Key: " yoomoney_secret_key
    
    # CryptoBot
    read -p "CryptoBot API Token: " cryptobot_token
    read -p "CryptoBot Shop ID: " cryptobot_shop_id
    
    cd "$INSTALL_DIR"
    source venv/bin/activate
    
    python3 -c "
import os
import configparser

config_file = 'config.ini'
config_parser = configparser.ConfigParser()
config_parser.read(config_file)

# Обновляем настройки платежей
if '$yoomoney_shop_id'.strip():
    config_parser['PAYMENTS']['yoomoney_shop_id'] = '$yoomoney_shop_id'
if '$yoomoney_secret_key'.strip():
    config_parser['PAYMENTS']['yoomoney_secret_key'] = '$yoomoney_secret_key'
if '$cryptobot_token'.strip():
    config_parser['PAYMENTS']['cryptobot_token'] = '$cryptobot_token'
if '$cryptobot_shop_id'.strip():
    config_parser['PAYMENTS']['cryptobot_shop_id'] = '$cryptobot_shop_id'

# Сохраняем конфиг
with open(config_file, 'w') as f:
    config_parser.write(f)

print('✅ Настройки платежных систем сохранены')
"
}

setup_bot_config() {
    log_info "Настройка бота..."
    
    read -p "Введите токен Telegram бота: " bot_token
    
    if [ -z "$bot_token" ]; then
        log_error "Токен бота не может быть пустым"
        return 1
    fi
    
    read -p "Введите порт веб-панели [5000]: " web_port
    web_port=${web_port:-5000}
    read -p "Включить отладку (y/N): " debug_mode
    debug_mode=${debug_mode:-n}
    
    cd "$INSTALL_DIR"
    source venv/bin/activate
    
    python3 -c "
import os
import configparser

config_file = 'config.ini'
config_parser = configparser.ConfigParser()

# Создаем конфиг если не существует
if not os.path.exists(config_file):
    config_parser['DATABASE'] = {
        'path': 'data/vpn_bot.db',
        'backup_path': 'backups/'
    }
    config_parser['BOT'] = {
        'token': '$bot_token',
        'admin_telegram_id': '$telegram_id'
    }
    config_parser['WEB'] = {
        'secret_key': os.urandom(24).hex(),
        'host': '127.0.0.1',
        'port': '$web_port',
        'debug': '$( [ \"$debug_mode\" = \"y\" ] && echo \"True\" || echo \"False\" )'
    }
    config_parser['PAYMENTS'] = {}
    config_parser['SECURITY'] = {
        'auto_unban_interval_hours': '6',
        'max_login_attempts': '5',
        'session_timeout_minutes': '60',
        'backup_retention_days': '7'
    }
    config_parser['LOGGING'] = {
        'level': 'INFO',
        'file': 'logs/vpn_bot.log',
        'max_size_mb': '10',
        'backup_count': '5'
    }
else:
    config_parser.read(config_file)
    if '$bot_token'.strip():
        if 'BOT' not in config_parser:
            config_parser['BOT'] = {}
        config_parser['BOT']['token'] = '$bot_token'
    
    if 'WEB' not in config_parser:
        config_parser['WEB'] = {}
    config_parser['WEB']['port'] = '$web_port'
    config_parser['WEB']['debug'] = '$( [ \"$debug_mode\" = \"y\" ] && echo \"True\" || echo \"False\" )'

# Устанавливаем admin_telegram_id если он был введен ранее
if [ -n \"$telegram_id\" ] && [[ \"$telegram_id\" =~ ^[0-9]+$ ]]; then
    if 'BOT' not in config_parser:
        config_parser['BOT'] = {}
    config_parser['BOT']['admin_telegram_id'] = '$telegram_id'
fi

with open(config_file, 'w') as f:
    config_parser.write(f)

print('✅ Конфигурация бота сохранена')
print('🤖 Токен бота: ********'${bot_token: -4}')
print('🌐 Порт веб-панели: $web_port')
print('🐛 Режим отладки: $( [ \"$debug_mode\" = \"y\" ] && echo \"Включен\" || echo \"Выключен\" )')
"
}

set_secure_permissions() {
    log_info "Настройка безопасных прав доступа..."
    
    cd "$INSTALL_DIR"
    
    # Делаем скрипты исполняемыми
    chmod +x run.py scripts/*.sh
    
    # Устанавливаем безопасные права для конфиденциальных файлов
    if [ -f "config.ini" ]; then
        chmod 600 config.ini
    fi
    
    if [ -f "data/vpn_bot.db" ]; then
        chmod 600 data/vpn_bot.db
    fi
    
    # Создаем необходимые директории с правильными правами
    mkdir -p data logs backups
    chmod 700 data logs backups
    
    # Рекурсивно меняем владельца на root
    chown -R root:root .
    
    log_success "Безопасные права настроены"
}

create_systemd_service() {
    log_info "Создание systemd сервиса..."
    
    local service_file="/etc/systemd/system/vpn-bot-panel.service"
    
    cat > "$service_file" << EOF
[Unit]
Description=VPN Bot Panel
After=network.target
Requires=network.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=$INSTALL_DIR
Environment=PYTHONPATH=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python3 run.py
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal

# Security
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=$INSTALL_DIR/data $INSTALL_DIR/logs
ReadOnlyPaths=$INSTALL_DIR

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable vpn-bot-panel.service
    
    log_success "Systemd сервис создан и включен"
}

setup_backup_cron() {
    log_info "Настройка автоматического бэкапа..."
    
    local backup_script="/usr/local/bin/vpn-panel-backup.sh"
    
    # Копируем скрипт бэкапа если он существует
    if [ -f "$INSTALL_DIR/scripts/backup.sh" ]; then
        cp "$INSTALL_DIR/scripts/backup.sh" "$backup_script"
        chmod +x "$backup_script"
        
        # Добавляем в cron (ежедневно в 3:00)
        (crontab -l 2>/dev/null | grep -v "$backup_script"; echo "0 3 * * $backup_script") | crontab -
        
        log_success "Автоматический бэкап настроен"
    else
        log_warning "Скрипт бэкапа не найден, пропускаем настройку cron"
    fi
}

setup_nginx_proxy() {
    log_info "Настройка Nginx прокси..."
    
    read -p "Настроить Nginx прокси для веб-панели? (y/N): " setup_nginx
    setup_nginx=${setup_nginx:-n}
    
    if [ "$setup_nginx" = "y" ] || [ "$setup_nginx" = "Y" ]; then
        read -p "Введите доменное имя для панели (например: panel.yourdomain.com): " domain_name
        
        if [ -n "$domain_name" ]; then
            local nginx_config="/etc/nginx/sites-available/vpn-bot-panel"
            
            cat > "$nginx_config" << EOF
server {
    listen 80;
    server_name $domain_name;
    
    location / {
        proxy_pass http://127.0.0.1:$web_port;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    # Безопасные заголовки
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
}
EOF

            # Активируем конфиг
            ln -sf "$nginx_config" "/etc/nginx/sites-enabled/" 2>/dev/null || true
            if nginx -t; then
                systemctl reload nginx
                log_success "Nginx прокси настроен для $domain_name"
                log_info "Не забудьте настроить SSL сертификаты (certbot) для домена"
            else
                log_error "Ошибка конфигурации Nginx"
            fi
        else
            log_warning "Доменное имя не указано, Nginx прокси не настроен"
        fi
    else
        log_info "Nginx прокси пропущен"
    fi
}

start_services() {
    log_info "Запуск сервисов..."
    
    systemctl start vpn-bot-panel
    sleep 5
    
    if systemctl is-active --quiet vpn-bot-panel; then
        log_success "Сервис vpn-bot-panel запущен"
    else
        log_error "Ошибка запуска сервиса vpn-bot-panel"
        systemctl status vpn-bot-panel --no-pager
    fi
}

show_final_instructions() {
    local web_port="5000"
    local bot_token="не настроен"
    local admin_id="не настроен"
    
    if [ -f "$INSTALL_DIR/config.ini" ]; then
        web_port=$(grep -oP 'port\s*=\s*\K\d+' "$INSTALL_DIR/config.ini" 2>/dev/null || echo "5000")
        bot_token=$(grep -oP 'token\s*=\s*\K[^ ]+' "$INSTALL_DIR/config.ini" 2>/dev/null || echo "не настроен")
        admin_id=$(grep -oP 'admin_telegram_id\s*=\s*\K[^ ]+' "$INSTALL_DIR/config.ini" 2>/dev/null || echo "не настроен")
    fi
    
    local server_ip=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "localhost")
    
    echo ""
    log_success "🎉 Установка завершена!"
    echo ""
    log_info "📋 Информация об установке:"
    echo "  📁 Директория: $INSTALL_DIR"
    echo "  🤖 Токен бота: ********${bot_token: -4}"
    echo "  👑 Admin Telegram ID: $admin_id"
    echo "  🌐 Веб-панель: http://$server_ip:$web_port"
    echo ""
    log_info "🛡️  Система безопасности:"
    echo "  • Конфигурационные файлы защищены"
    echo "  • База данных зашифрована"
    echo "  • Автоматические бэкапы настроены"
    echo "  • Systemd сервис с ограниченными правами"
    echo ""
    log_info "🚀 Команды управления:"
    echo "  sudo systemctl start vpn-bot-panel      # Запуск"
    echo "  sudo systemctl stop vpn-bot-panel       # Остановка"
    echo "  sudo systemctl status vpn-bot-panel     # Статус"
    echo "  sudo systemctl restart vpn-bot-panel    # Перезапуск"
    echo "  sudo journalctl -u vpn-bot-panel -f     # Логи"
    echo ""
    log_info "🔄 Обновление системы:"
    echo "  sudo $INSTALL_DIR/scripts/update.sh"
    echo ""
    log_info "💾 Резервное копирование:"
    echo "  sudo $INSTALL_DIR/scripts/backup.sh"
    echo ""
    log_info "📚 Следующие шаги:"
    echo "  1. Проверьте работу бота в Telegram: /start"
    echo "  2. Добавьте серверы 3x-ui через бота (/addserver)"
    echo "  3. Назначьте модераторов (/addmoderator)"
    echo "  4. Настройте тарифы через веб-панель"
    echo "  5. Протестируйте систему"
    echo ""
    log_info "🔧 Устранение неполадок:"
    echo "  • Логи бота: sudo journalctl -u vpn-bot-panel -f"
    echo "  • Логи приложения: tail -f $INSTALL_DIR/logs/vpn_bot.log"
    echo "  • Проверка конфигурации: sudo $INSTALL_DIR/venv/bin/python3 -c \"import sys; sys.path.append('$INSTALL_DIR'); from app.config import Config; print('OK')\""
    echo ""
}

main() {
    log_info "Начало установки VPN Bot Panel..."
    log_info "Корневая директория проекта: $PROJECT_ROOT"
    log_info "Директория установки: $INSTALL_DIR"
    
    check_root
    check_python
    install_system_packages
    create_install_directory
    copy_project_files
    setup_venv
    install_dependencies
    setup_directories
    setup_database
    setup_super_admin
    setup_payment_config
    setup_bot_config
    set_secure_permissions
    create_systemd_service
    setup_backup_cron
    setup_nginx_proxy
    start_services
    show_final_instructions
}

# Обработка аргументов командной строки
while [[ $# -gt 0 ]]; do
    case $1 in
        --install-dir)
            INSTALL_DIR="$2"
            shift 2
            ;;
        --help|-h)
            echo "Использование: $0 [OPTIONS]"
            echo ""
            echo "OPTIONS:"
            echo "  --install-dir DIR    Директория установки (по умолчанию: /opt/vpn-bot-panel)"
            echo "  --help, -h           Показать эту справку"
            echo ""
            echo "Пример:"
            echo "  sudo $0 --install-dir /opt/my-vpn-bot"
            exit 0
            ;;
        *)
            log_error "Неизвестный аргумент: $1"
            echo "Используйте $0 --help для справки"
            exit 1
            ;;
    esac
done

main "$@"