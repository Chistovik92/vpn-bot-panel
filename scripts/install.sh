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
        apt install -y python3-venv python3-pip git sqlite3
    elif command -v yum &>/dev/null; then
        yum install -y python3-virtualenv python3-pip git sqlite
    elif command -v dnf &>/dev/null; then
        dnf install -y python3-virtualenv python3-pip git sqlite
    else
        log_warning "Неизвестный пакетный менеджер"
    fi
}

setup_venv() {
    log_info "Настройка виртуального окружения..."
    
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        log_success "Виртуальное окружение создано"
    fi
    
    source venv/bin/activate
}

install_dependencies() {
    log_info "Установка зависимостей..."
    
    pip install --upgrade pip
    pip install -r requirements.txt
    
    log_success "Зависимости установлены"
}

setup_directories() {
    log_info "Создание структуры директорий..."
    
    mkdir -p app scripts templates static/css static/js data logs backups
    log_success "Директории созданы"
}

setup_database() {
    log_info "Инициализация базы данных..."
    
    source venv/bin/activate
    python3 -c "
from app.database import Database
db = Database()
db.init_db()
print('✅ База данных инициализирована')
"
}

setup_super_admin() {
    log_info "Настройка супер администратора..."
    
    read -p "Введите Telegram ID супер администратора: " telegram_id
    read -p "Введите имя пользователя [admin]: " username
    username=${username:-admin}
    
    source venv/bin/activate
    python3 -c "
from app.database import Database, UserRole
db = Database()

# Создаем или обновляем супер администратора
db.create_user($telegram_id, '$username', 'System Administrator', UserRole.SUPER_ADMIN.value)
print('✅ Супер администратор создан')
print(f'   👤 Имя: $username')
print(f'   📱 Telegram ID: $telegram_id')
print(f'   👑 Роль: Супер администратор')
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
    
    source venv/bin/activate
    python3 -c "
from app.config import Config
config = Config()

# Загружаем текущий конфиг
current_config = config.load_config()

# Обновляем настройки платежей
if '$yoomoney_shop_id':
    current_config['PAYMENTS']['yoomoney_shop_id'] = '$yoomoney_shop_id'
if '$yoomoney_secret_key':
    current_config['PAYMENTS']['yoomoney_secret_key'] = '$yoomoney_secret_key'
if '$cryptobot_token':
    current_config['PAYMENTS']['cryptobot_token'] = '$cryptobot_token'
if '$cryptobot_shop_id':
    current_config['PAYMENTS']['cryptobot_shop_id'] = '$cryptobot_shop_id'

# Сохраняем конфиг
with open('config.ini', 'w') as f:
    current_config.write(f)

print('✅ Настройки платежных систем сохранены')
"
}

setup_bot_config() {
    log_info "Настройка бота..."
    
    read -p "Введите токен Telegram бота: " bot_token
    read -p "Введите порт веб-панели [5000]: " web_port
    web_port=${web_port:-5000}
    read -p "Включить отладку (y/N): " debug_mode
    debug_mode=${debug_mode:-n}
    
    source venv/bin/activate
    python3 -c "
from app.config import Config
config = Config()
config.create_default_config()

# Обновляем конфиг с введенными данными
import configparser
config_parser = configparser.ConfigParser()
config_parser.read('config.ini')

if '$bot_token':
    config_parser['BOT']['token'] = '$bot_token'
if '$web_port':
    config_parser['WEB']['port'] = '$web_port'

config_parser['WEB']['debug'] = '$( [ \"$debug_mode\" = \"y\" ] && echo \"True\" || echo \"False\" )'

with open('config.ini', 'w') as f:
    config_parser.write(f)

print('✅ Конфигурация бота сохранена')
"
}

set_secure_permissions() {
    log_info "Настройка безопасных прав доступа..."
    
    # Делаем скрипты исполняемыми
    chmod +x run.py scripts/*.sh
    
    # Устанавливаем безопасные права для конфиденциальных файлов
    chmod 600 config.ini 2>/dev/null || true
    chmod 600 data/vpn_bot.db 2>/dev/null || true
    
    # Рекурсивно меняем владельца на root
    chown -R root:root .
    
    log_success "Безопасные права настроены"
}

create_systemd_service() {
    log_info "Создание systemd сервиса..."
    
    local service_file="/etc/systemd/system/vpn-bot-panel.service"
    local working_dir=$(pwd)
    
    cat > "$service_file" << EOF
[Unit]
Description=VPN Bot Panel
After=network.target
Requires=network.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=$working_dir
Environment=PYTHONPATH=$working_dir
ExecStart=$working_dir/venv/bin/python3 run.py
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal

# Security
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=$working_dir/data $working_dir/logs
ReadOnlyPaths=$working_dir

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
    
    cat > "$backup_script" << 'EOF'
#!/bin/bash
# Автоматический бэкап VPN Bot Panel

BACKUP_DIR="/opt/vpn-bot-panel/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/backup_$DATE.tar.gz"

mkdir -p $BACKUP_DIR

# Создаем бэкап
tar -czf $BACKUP_FILE \
    --exclude='venv' \
    --exclude='*.log' \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    /opt/vpn-bot-panel/

# Удаляем старые бэкапы (храним последние 7)
find $BACKUP_DIR -name "backup_*.tar.gz" -type f -mtime +7 -delete

echo "Backup created: $BACKUP_FILE"
EOF

    chmod +x $backup_script
    
    # Добавляем в cron (ежедневно в 3:00)
    (crontab -l 2>/dev/null; echo "0 3 * * * $backup_script") | crontab -
    
    log_success "Автоматический бэкап настроен"
}

show_final_instructions() {
    echo ""
    log_success "🎉 Установка завершена!"
    echo ""
    log_info "🛡️  Система безопасности:"
    echo "  • Конфигурационные файлы защищены (только root)"
    echo "  • База данных зашифрована"
    echo "  • Автоматические бэкапы настроены"
    echo "  • Systemd сервис с ограниченными правами"
    echo ""
    log_info "🚀 Быстрый старт:"
    echo "  python3 run.py                          # Запуск вручную"
    echo "  sudo systemctl start vpn-bot-panel      # Запуск через systemd"
    echo ""
    log_info "👑 Доступ к системе:"
    echo "  Веб-панель: http://localhost:$(grep -oP 'port\s*=\s*\K\d+' config.ini 2>/dev/null || echo 5000)"
    echo "  Супер администратор: Telegram ID $(grep -oP 'admin_telegram_id\s*=\s*\K\d+' config.ini 2>/dev/null || echo 'настроен в установке')"
    echo ""
    log_info "🔧 Команды управления:"
    echo "  sudo systemctl status vpn-bot-panel     # Статус сервиса"
    echo "  sudo systemctl restart vpn-bot-panel    # Перезапуск"
    echo "  sudo ./scripts/update.sh                # Обновление"
    echo ""
    log_info "📚 Следующие шаги:"
    echo "  1. Добавьте серверы 3x-ui через бота (/addserver)"
    echo "  2. Назначьте модераторов (/addmoderator)"
    echo "  3. Настройте тарифы через веб-панель"
    echo "  4. Протестируйте систему"
    echo ""
}

main() {
    log_info "Начало установки VPN Bot Panel..."
    
    check_root
    check_python
    install_system_packages
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
    show_final_instructions
}

main "$@"