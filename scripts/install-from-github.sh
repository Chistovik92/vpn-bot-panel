#!/bin/bash

set -e

echo "🚀 Автоматическая установка VPN Bot Panel с GitHub..."

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
TEMP_DIR="/tmp/vpn-bot-panel-install"

check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_success "Проверка прав: root"
    else
        log_error "Требуются права root"
        log_info "Запустите: sudo bash <(curl -sSL https://raw.githubusercontent.com/Chistovik92/vpn-bot-panel/Dev_Bot-plan/install-from-github.sh)"
        exit 1
    fi
}

check_dependencies() {
    log_info "Проверка системных зависимостей..."
    
    local missing_deps=()
    
    if ! command -v git &>/dev/null; then
        missing_deps+=("git")
    fi
    
    if ! command -v curl &>/dev/null; then
        missing_deps+=("curl")
    fi
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        log_warning "Необходимо установить зависимости: ${missing_deps[*]}"
        
        if command -v apt &>/dev/null; then
            apt update
            apt install -y "${missing_deps[@]}"
            log_success "Зависимости установлены"
        else
            log_error "Установите зависимости вручную: ${missing_deps[*]}"
            exit 1
        fi
    else
        log_success "Все зависимости установлены"
    fi
}

check_disk_space() {
    log_info "Проверка свободного места на диске..."
    
    local available_kb=$(df / | awk 'NR==2 {print $4}')
    local available_mb=$((available_kb / 1024))
    local min_space_mb=500
    
    if [ "$available_mb" -lt "$min_space_mb" ]; then
        log_error "Недостаточно свободного места!"
        log_info "Доступно: ${available_mb} MB"
        log_info "Требуется: ${min_space_mb} MB"
        log_info ""
        log_info "Запустите очистку диска:"
        log_info "sudo bash <(curl -sSL https://raw.githubusercontent.com/Chistovik92/vpn-bot-panel/Dev_Bot-plan/scripts/cleanup.sh)"
        exit 1
    else
        log_success "Свободного места достаточно: ${available_mb} MB"
    fi
}

download_repository() {
    log_info "Загрузка репозитория..."
    
    # Создаем временную директорию
    rm -rf "$TEMP_DIR"
    mkdir -p "$TEMP_DIR"
    
    # Клонируем репозиторий
    if git clone --branch "$BRANCH" --depth 1 "$REPO_URL" "$TEMP_DIR" 2>/dev/null; then
        log_success "Репоизиторий загружен"
    else
        log_error "Ошибка загрузки репозитория"
        log_info "Проверьте:"
        log_info "1. Доступность GitHub"
        log_info "2. Название ветки: $BRANCH"
        log_info "3. Наличие интернет-соединения"
        exit 1
    fi
}

setup_installation() {
    log_info "Настройка установки..."
    
    # Копируем файлы в целевую директорию
    if [ ! -d "$INSTALL_DIR" ]; then
        mkdir -p "$INSTALL_DIR"
    fi
    
    # Копируем основные файлы
    cp -r "$TEMP_DIR"/app "$INSTALL_DIR"/
    cp -r "$TEMP_DIR"/scripts "$INSTALL_DIR"/
    cp -r "$TEMP_DIR"/templates "$INSTALL_DIR"/ 2>/dev/null || true
    cp -r "$TEMP_DIR"/static "$INSTALL_DIR"/ 2>/dev/null || true
    cp -r "$TEMP_DIR"/docs "$INSTALL_DIR"/ 2>/dev/null || true
    
    cp "$TEMP_DIR"/requirements.txt "$INSTALL_DIR"/
    cp "$TEMP_DIR"/config.ini.example "$INSTALL_DIR"/config.ini 2>/dev/null || true
    cp "$TEMP_DIR"/run.py "$INSTALL_DIR"/
    cp "$TEMP_DIR"/LICENSE "$INSTALL_DIR"/ 2>/dev/null || true
    cp "$TEMP_DIR"/README.md "$INSTALL_DIR"/ 2>/dev/null || true
    
    # Создаем необходимые директории
    mkdir -p "$INSTALL_DIR/data" "$INSTALL_DIR/logs" "$INSTALL_DIR/backups"
    
    log_success "Файлы скопированы в $INSTALL_DIR"
}

install_system_packages() {
    log_info "Установка системных пакетов..."
    
    if command -v apt &>/dev/null; then
        apt update
        
        # Устанавливаем только необходимые пакеты
        apt install -y --no-install-recommends \
            python3 \
            python3-venv \
            python3-pip \
            sqlite3 \
            nginx \
            curl
        
        log_success "Системные пакеты установлены"
    elif command -v yum &>/dev/null; then
        yum install -y python3 python3-virtualenv python3-pip sqlite nginx curl
        log_success "Системные пакеты установлены"
    else
        log_warning "Неизвестный пакетный менеджер, требуется ручная установка Python 3.8+"
    fi
}

run_install_script() {
    log_info "Запуск скрипта установки..."
    
    cd "$INSTALL_DIR"
    
    if [ -f "scripts/install.sh" ]; then
        chmod +x scripts/install.sh
        
        # Запускаем установку в неинтерактивном режиме
        log_info "Установка может занять несколько минут..."
        ./scripts/install.sh --non-interactive
    else
        log_error "Скрипт установки не найден"
        exit 1
    fi
}

cleanup_temp() {
    log_info "Очистка временных файлов..."
    rm -rf "$TEMP_DIR"
    log_success "Временные файлы удалены"
}

show_quick_install() {
    log_info "🚀 Быстрая установка (автоматический режим)..."
    
    cd "$INSTALL_DIR"
    
    # Создаем базовый конфиг
    cat > config.ini << 'EOF'
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
    
    # Настраиваем venv и зависимости
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    
    # Инициализируем БД
    python3 -c "import sys; sys.path.append('.'); from app.database import Database; db = Database(); db.init_db()"
    
    log_success "Быстрая установка завершена"
}

show_final_instructions() {
    echo ""
    log_success "🎉 Установка VPN Bot Panel завершена!"
    echo ""
    log_info "📋 Следующие шаги:"
    echo "  1. Настройте конфигурацию:"
    echo "     sudo nano $INSTALL_DIR/config.ini"
    echo ""
    echo "  2. Установите токен бота и ID администратора"
    echo ""
    echo "  3. Запустите систему:"
    echo "     sudo systemctl start vpn-bot-panel"
    echo ""
    echo "  4. Проверьте статус:"
    echo "     sudo systemctl status vpn-bot-panel"
    echo ""
    log_info "🌐 Веб-панель будет доступна по:"
    echo "     http://ваш-сервер:5000"
    echo ""
    log_info "📚 Документация:"
    echo "     $INSTALL_DIR/docs/"
    echo ""
}

main() {
    log_info "Начало автоматической установки с GitHub..."
    log_info "Репозиторий: $REPO_URL"
    log_info "Ветка: $BRANCH"
    log_info "Директория установки: $INSTALL_DIR"
    
    check_root
    check_dependencies
    check_disk_space
    download_repository
    setup_installation
    install_system_packages
    
    # Проверяем, запрошена ли неинтерактивная установка
    if [[ " $* " == *" --non-interactive "* ]]; then
        show_quick_install
    else
        run_install_script
    fi
    
    cleanup_temp
    show_final_instructions
}

# Обработка аргументов
while [[ $# -gt 0 ]]; do
    case $1 in
        --install-dir)
            INSTALL_DIR="$2"
            shift 2
            ;;
        --branch)
            BRANCH="$2"
            shift 2
            ;;
        --non-interactive)
            shift
            ;;
        --help|-h)
            echo "Использование: $0 [OPTIONS]"
            echo ""
            echo "OPTIONS:"
            echo "  --install-dir DIR    Директория установки (по умолчанию: /opt/vpn-bot-panel)"
            echo "  --branch BRANCH      Ветка GitHub (по умолчанию: Dev_Bot-plan)"
            echo "  --non-interactive    Неинтерактивный режим"
            echo "  --help, -h           Показать эту справку"
            echo ""
            echo "Примеры:"
            echo "  curl -sSL https://raw.githubusercontent.com/.../install-from-github.sh | sudo bash"
            echo "  curl -sSL ... | sudo bash -s -- --install-dir /opt/my-vpn --non-interactive"
            exit 0
            ;;
        *)
            log_error "Неизвестный аргумент: $1"
            exit 1
            ;;
    esac
done

main "$@"