#!/bin/bash

set -e

echo "🚀 Универсальный установщик VPN Bot Panel"

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

show_usage() {
    echo "Использование: $0 [OPTIONS]"
    echo ""
    echo "OPTIONS:"
    echo "  --minimal              Минимальная установка (меньше места)"
    echo "  --install-dir DIR      Директория установки (по умолчанию: /opt/vpn-bot-panel)"
    echo "  --branch BRANCH        Ветка GitHub (по умолчанию: Dev_Bot-plan)"
    echo "  --cleanup              Очистка диска перед установкой"
    echo "  --help, -h             Показать эту справку"
    echo ""
    echo "Примеры:"
    echo "  $0                              # Стандартная установка"
    echo "  $0 --minimal                    # Минимальная установка"
    echo "  $0 --install-dir /opt/my-vpn    # Установка в другую директорию"
    echo "  $0 --cleanup --minimal          # Очистка + минимальная установка"
    echo ""
    echo "Быстрая установка одной командой:"
    echo "  curl -sSL https://raw.githubusercontent.com/Chistovik92/vpn-bot-panel/Dev_Bot-plan/install.sh | sudo bash -s -- --minimal"
}

download_and_run() {
    local script_url="$1"
    local script_name="$2"
    
    log_info "Загрузка $script_name..."
    
    # Скачиваем скрипт
    if curl -sSL "$script_url" -o "/tmp/$script_name"; then
        chmod +x "/tmp/$script_name"
        log_success "Скрипт загружен: $script_name"
        
        # Запускаем скрипт с оставшимися аргументами
        "/tmp/$script_name" "${@:3}"
        
        # Очищаем
        rm -f "/tmp/$script_name"
    else
        log_error "Ошибка загрузки $script_name"
        return 1
    fi
}

run_cleanup() {
    log_info "Запуск очистки диска..."
    download_and_run \
        "https://raw.githubusercontent.com/Chistovik92/vpn-bot-panel/Dev_Bot-plan/scripts/cleanup.sh" \
        "cleanup.sh"
}

run_full_install() {
    local install_dir="$1"
    local branch="$2"
    
    log_info "Запуск полной установки..."
    download_and_run \
        "https://raw.githubusercontent.com/Chistovik92/vpn-bot-panel/$branch/install-from-github.sh" \
        "install-from-github.sh" \
        --install-dir "$install_dir" \
        --branch "$branch"
}

run_minimal_install() {
    local install_dir="$1"
    local branch="$2"
    
    log_info "Запуск минимальной установки..."
    download_and_run \
        "https://raw.githubusercontent.com/Chistovik92/vpn-bot-panel/$branch/install-minimal-from-github.sh" \
        "install-minimal-from-github.sh" \
        --install-dir "$install_dir" \
        --branch "$branch"
}

main() {
    local MODE="full"
    local INSTALL_DIR="/opt/vpn-bot-panel"
    local BRANCH="Dev_Bot-plan"
    local RUN_CLEANUP=false
    
    # Разбор аргументов
    while [[ $# -gt 0 ]]; do
        case $1 in
            --minimal)
                MODE="minimal"
                shift
                ;;
            --install-dir)
                INSTALL_DIR="$2"
                shift 2
                ;;
            --branch)
                BRANCH="$2"
                shift 2
                ;;
            --cleanup)
                RUN_CLEANUP=true
                shift
                ;;
            --help|-h)
                show_usage
                exit 0
                ;;
            *)
                log_error "Неизвестный аргумент: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Проверка прав
    if [[ $EUID -ne 0 ]]; then
        log_error "Требуются права root"
        log_info "Запустите: sudo $0 $*"
        exit 1
    fi
    
    log_info "Режим: $MODE"
    log_info "Директория: $INSTALL_DIR"
    log_info "Ветка: $BRANCH"
    
    # Очистка диска если нужно
    if [ "$RUN_CLEANUP" = true ]; then
        run_cleanup
    fi
    
    # Запуск установки
    case "$MODE" in
        "full")
            run_full_install "$INSTALL_DIR" "$BRANCH"
            ;;
        "minimal")
            run_minimal_install "$INSTALL_DIR" "$BRANCH"
            ;;
    esac
}

main "$@"