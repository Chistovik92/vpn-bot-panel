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

check_disk_space() {
    log_info "Проверка свободного места на диске..."
    
    local available_kb=$(df / | awk 'NR==2 {print $4}')
    local available_mb=$((available_kb / 1024))
    local min_space_mb=500  # Минимум 500MB
    
    if [ "$available_mb" -lt "$min_space_mb" ]; then
        log_error "Недостаточно свободного места на диске!"
        log_info "Доступно: ${available_mb} MB"
        log_info "Требуется: ${min_space_mb} MB"
        log_info ""
        log_info "Запустите очистку диска:"
        log_info "sudo ./scripts/cleanup.sh"
        log_info ""
        log_info "Или освободите место вручную:"
        log_info "sudo apt clean && sudo apt autoremove --purge"
        exit 1
    else
        log_success "Свободного места достаточно: ${available_mb} MB"
    fi
}

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

install_minimal_packages() {
    log_info "Установка минимального набора пакетов..."
    
    # Очищаем кэш перед установкой
    apt clean 2>/dev/null || true
    
    if command -v apt &>/dev/null; then
        apt update
        
        # Устанавливаем только самые необходимые пакеты
        apt install -y --no-install-recommends \
            python3 \
            python3-venv \
            python3-pip \
            sqlite3 \
            curl
        
        log_success "Минимальные пакеты установлены"
    else
        log_error "Не удалось установить пакеты (apt не найден)"
        exit 1
    fi
}

install_full_packages() {
    log_info "Установка дополнительных пакетов..."
    
    if command -v apt &>/dev/null; then
        apt install -y \
            git \
            nginx \
            systemd
        
        log_success "Дополнительные пакеты установлены"
    else
        log_warning "Не удалось установить дополнительные пакеты"
    fi
}

create_install_directory() {
    log_info "Создание директории установки..."
    
    if [ ! -d "$INSTALL_DIR" ]; then
        mkdir -p "$INSTALL_DIR"
        log_success "Директория создана: $INSTALL_DIR"
    else
        log_warning "Директория уже существует: $INSTALL_DIR"
        
        read -p "Очистить директорию перед установкой? (y/N): " clean_dir
        if [ "$clean_dir" = "y" ] || [ "$clean_dir" = "Y" ]; then
            rm -rf "$INSTALL_DIR"/*
            log_success "Директория очищена"
        fi
    fi
}

# ... остальные функции остаются такими же как в предыдущей версии ...

main() {
    log_info "Начало установки VPN Bot Panel..."
    log_info "Корневая директория проекта: $PROJECT_ROOT"
    log_info "Директория установки: $INSTALL_DIR"
    
    check_root
    check_disk_space
    check_python
    install_minimal_packages
    create_install_directory
    copy_project_files
    setup_venv
    install_dependencies
    setup_directories
    setup_database
    setup_super_admin
    setup_payment_config
    setup_bot_config
    install_full_packages
    set_secure_permissions
    create_systemd_service
    setup_backup_cron
    setup_nginx_proxy
    start_services
    show_final_instructions
}

# ... остальная часть скрипта ...