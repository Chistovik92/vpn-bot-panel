#!/bin/bash

# VPN Bot Panel - Удаление
set -e

SERVICE_NAME="vpnbot"
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log_info()    { echo -e "${BLUE}[INFO] $1${NC}"; }
log_success() { echo -e "${GREEN}[OK]   $1${NC}"; }
log_warning() { echo -e "${YELLOW}[WARN] $1${NC}"; }
log_error()   { echo -e "${RED}[ERR]  $1${NC}"; }

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "Требуются права root: sudo $0"
        exit 1
    fi
}

check_project_dir() {
    if [ ! -f "run.py" ]; then
        log_error "Запустите скрипт из директории проекта VPN Bot Panel"
        exit 1
    fi
}

confirm_uninstall() {
    echo ""
    log_warning "ВНИМАНИЕ: будут удалены:"
    echo "   - systemd-сервисы (vpnbot, vpn-bot-panel, vpn-admin-panel)"
    echo "   - виртуальное окружение (venv/)"
    echo "   - база данных и все данные (data/)"
    echo "   - config.ini, логи, кэш Python"
    echo ""
    echo "Резервная копия БД и конфига будет сохранена в текущей директории."
    echo "Это действие нельзя отменить!"
    read -rp "Введите 'УДАЛИТЬ' для подтверждения: " -r
    if [[ ! $REPLY == "УДАЛИТЬ" ]]; then
        log_info "Удаление отменено."
        exit 0
    fi
}

backup_data() {
    local backup_dir="uninstall_backup_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"
    [ -f data/vpn_bot.db ] && cp data/vpn_bot.db "$backup_dir/" && \
        log_success "БД сохранена в $backup_dir/"
    [ -f config.ini ] && cp config.ini "$backup_dir/" && chmod 600 "$backup_dir/config.ini"
}

remove_systemd_services() {
    for svc in "$SERVICE_NAME" vpn-bot-panel vpn-admin-panel; do
        systemctl stop "$svc.service" 2>/dev/null || true
        systemctl disable "$svc.service" >/dev/null 2>&1 || true
        [ -f "/etc/systemd/system/$svc.service" ] && rm -f "/etc/systemd/system/$svc.service"
    done
    systemctl daemon-reload
    log_success "Systemd сервисы остановлены и удалены"
}

remove_components() {
    rm -rf venv
    log_success "venv удалён"

    rm -rf data logs backups
    log_success "data/, logs/, backups/ удалены"

    rm -f config.ini panel_config.json install_credentials.txt
    log_success "Файлы конфигурации удалены"

    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete 2>/dev/null || true
    find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
    log_success "Кэш Python очищен"
}

show_final_message() {
    echo ""
    log_success "Удаление завершено!"
    log_info "Код репозитория остался на месте. Резервные копии: uninstall_backup_*/"
}

main() {
    check_project_dir
    check_root
    confirm_uninstall
    backup_data
    remove_systemd_services
    remove_components
    show_final_message
}

main "$@"
