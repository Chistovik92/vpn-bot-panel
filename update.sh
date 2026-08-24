#!/bin/bash

# VPN Bot Panel - Обновление
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
    if [ ! -f "app/run.py" ] && [ ! -f "run.py" ]; then
        log_error "Запустите скрипт из директории проекта VPN Bot Panel"
        exit 1
    fi
}

create_backup() {
    local backup_dir="backups/preupdate_$(date +%Y%m%d_%H%M%S)"
    log_info "Резервная копия перед обновлением..."
    mkdir -p "$backup_dir"
    [ -f data/vpn_bot.db ] && cp data/vpn_bot.db "$backup_dir/" && log_success "БД сохранена"
    [ -f config.ini ] && cp config.ini "$backup_dir/" && chmod 600 "$backup_dir/config.ini" \
        && log_success "config.ini сохранён"
}

stop_services() {
    log_info "Остановка сервисов..."
    systemctl stop "${SERVICE_NAME}.service" 2>/dev/null || true
    # Устаревшие сервисы старых версий
    for old in vpn-bot-panel vpn-admin-panel; do
        if systemctl list-unit-files | grep -q "^$old\.service"; then
            systemctl stop "$old" 2>/dev/null || true
            systemctl disable "$old" >/dev/null 2>&1 || true
            rm -f "/etc/systemd/system/$old.service"
            log_success "Устаревший сервис $old удалён"
        fi
    done
    pkill -f "python bot.py" 2>/dev/null || true
    pkill -f "python run.py" 2>/dev/null || true
}

update_code() {
    log_info "Получение обновлений из main..."
    git fetch origin main
    local behind
    behind=$(git rev-list --count HEAD..origin/main)
    if [ "$behind" = "0" ]; then
        log_info "Обновлений нет, актуальная версия"
    else
        log_info "Новых коммитов: $behind"
        git reset --hard origin/main
        log_success "Код обновлён до $(git rev-parse --short HEAD)"
    fi
}

update_dependencies() {
    if [ ! -x venv/bin/python ]; then
        log_error "venv не найден. Выполните установку заново (install.sh)"
        exit 1
    fi
    log_info "Обновление зависимостей..."
    ./venv/bin/python -m pip install --upgrade pip -q
    ./venv/bin/python -m pip install -r requirements.txt -q
    log_success "Зависимости обновлены"
}

run_migrations() {
    log_info "Применение миграций БД и проверка конфигурации..."
    PYTHONPATH="$(pwd)" ./venv/bin/python -m app.manage init
    PYTHONPATH="$(pwd)" ./venv/bin/python -m app.manage check || true
    log_success "База данных в актуальном состоянии"
}

update_permissions() {
    chmod 600 config.ini 2>/dev/null || true
    chmod 600 data/vpn_bot.db* 2>/dev/null || true
    chmod +x Boot-main-ini update.sh uninstall.sh 2>/dev/null || true
}

ensure_service() {
    if ! systemctl list-unit-files | grep -q "^${SERVICE_NAME}\.service"; then
        log_warning "Сервис ${SERVICE_NAME}.service не найден."
        log_info "Запустите install.sh для создания сервиса, или запустите вручную:"
        log_info "  cd $(pwd) && nohup venv/bin/python run.py > logs/run.log 2>&1 &"
    fi
}

restart_service() {
    log_info "Перезапуск сервиса..."
    if systemctl restart "${SERVICE_NAME}.service"; then
        sleep 3
        if systemctl is-active --quiet "${SERVICE_NAME}.service"; then
            log_success "VPN Bot Panel запущена"
        else
            log_error "Сервис не поднялся: journalctl -u ${SERVICE_NAME} -n 50"
            exit 1
        fi
    else
        log_warning "systemd-сервис недоступен, запускаю вручную в фоне..."
        mkdir -p logs
        nohup venv/bin/python run.py > logs/run.log 2>&1 &
        log_success "Приложение запущено вручную (PID $!)"
    fi
}

main() {
    log_info "=== Обновление VPN Bot Panel ==="
    check_project_dir
    check_root
    create_backup
    stop_services
    update_code
    update_dependencies
    run_migrations
    update_permissions
    ensure_service
    restart_service

    echo ""
    log_success "Обновление завершено!"
    log_info "Резервная копия: backups/"
}

main "$@"
