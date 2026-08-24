#!/bin/bash

# VPN Bot Panel - Установщик (Linux)
# Устанавливает бота + веб-панель как единый systemd-сервис vpnbot.service
set -e

REPO_URL="https://github.com/Chistovik92/vpn-bot-panel.git"
INSTALL_DIR="/opt/vpn-bot-panel"
SERVICE_NAME="vpnbot"
BRANCH="main"

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

install_system_packages() {
    log_info "Установка системных пакетов..."
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        case ${ID} in
            debian|ubuntu)
                export DEBIAN_FRONTEND=noninteractive
                apt-get update -y
                apt-get install -y python3-venv python3-pip git curl
                ;;
            centos|rhel|rocky|almalinux|fedora)
                if command -v dnf >/dev/null 2>&1; then
                    dnf install -y python3-pip git curl
                else
                    yum install -y python3-pip git curl
                fi
                ;;
            alpine)
                apk add --no-cache python3 py3-pip git curl
                ;;
            *)
                log_warning "Неизвестный дистрибутив: ${ID}. Проверьте python3/git вручную."
                ;;
        esac
    fi
    command -v git >/dev/null || { log_error "git не установлен"; exit 1; }
    command -v python3 >/dev/null || { log_error "python3 не установлен"; exit 1; }
    log_success "Системные пакеты готовы"
}

check_python_version() {
    if ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)'; then
        log_error "Требуется Python 3.10+"
        exit 1
    fi
    log_success "Python: $(python3 --version)"
}

setup_repository() {
    if [ -d "$INSTALL_DIR/.git" ]; then
        log_info "Обновление существующего репозитория в $INSTALL_DIR..."
        git -C "$INSTALL_DIR" fetch origin "$BRANCH"
        git -C "$INSTALL_DIR" reset --hard "origin/$BRANCH"
    else
        log_info "Клонирование $REPO_URL в $INSTALL_DIR..."
        git clone --depth 1 -b "$BRANCH" "$REPO_URL" "$INSTALL_DIR"
    fi
    cd "$INSTALL_DIR"
    mkdir -p data logs backups
    log_success "Код готов: $(git rev-parse --short HEAD)"
}

create_venv() {
    if [ ! -x venv/bin/python ]; then
        log_info "Создание виртуального окружения..."
        rm -rf venv
        python3 -m venv venv
    fi
    ./venv/bin/python -m pip install --upgrade pip -q
    log_success "Виртуальное окружение готово"
}

install_dependencies() {
    log_info "Установка зависимостей из requirements.txt..."
    ./venv/bin/python -m pip install -r requirements.txt
    log_success "Зависимости установлены"
}

run_setup() {
    log_info "Интерактивная настройка (токен бота, админ, пароль панели)..."
    PYTHONPATH="$INSTALL_DIR" ./venv/bin/python install.py
}

set_permissions() {
    chmod 600 config.ini 2>/dev/null || true
    chmod 600 data/vpn_bot.db* 2>/dev/null || true
    chmod +x update.sh uninstall.sh Boot-main-ini 2>/dev/null || true
}

service_exists() {
    systemctl list-unit-files | grep -q "^$1\.service"
}

create_service() {
    # Миграция со старых сервисов (две единицы старой схемы)
    for old in vpn-bot-panel vpn-admin-panel; do
        if service_exists "$old"; then
            log_info "Удаление устаревшего сервиса $old.service..."
            systemctl stop "$old" 2>/dev/null || true
            systemctl disable "$old" 2>/dev/null || true
            rm -f "/etc/systemd/system/$old.service"
        fi
    done

    log_info "Создание systemd сервиса $SERVICE_NAME.service..."
    cat > "/etc/systemd/system/${SERVICE_NAME}.service" <<EOF
[Unit]
Description=VPN Bot Panel (Telegram bot + web panel)
After=network.target

[Service]
Type=simple
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python run.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload
    systemctl enable "${SERVICE_NAME}.service" -q
    log_success "Сервис создан и включён в автозапуск"
}

start_service() {
    log_info "Запуск сервиса..."
    if systemctl restart "${SERVICE_NAME}.service"; then
        sleep 3
        if systemctl is-active --quiet "${SERVICE_NAME}.service"; then
            log_success "VPN Bot Panel запущена"
        else
            log_error "Сервис не поднялся. Логи: journalctl -u ${SERVICE_NAME} -n 50"
            return 1
        fi
    else
        log_error "Не удалось запустить сервис"
        return 1
    fi
}

show_final_instructions() {
    local server_ip
    server_ip=$(curl -s --max-time 5 http://checkip.amazonaws.com 2>/dev/null || echo "<server-ip>")
    local port
    port=$(grep -E '^port' config.ini 2>/dev/null | head -1 | tr -dc '0-9')
    port=${port:-8080}
    echo ""
    log_success "Установка завершена!"
    echo ""
    echo "  Сервис:      systemctl status $SERVICE_NAME"
    echo "  Управление:  sudo $INSTALL_DIR/Boot-main-ini"
    echo "  Веб-панель:  http://$server_ip:$port  (логин = Telegram ID + пароль)"
    echo "  Логи:        journalctl -u $SERVICE_NAME -f  или  logs/"
    echo ""
    echo "  Пароль панели уже задан на шаге настройки."
    echo "  Сменить:     cd $INSTALL_DIR && sudo ./venv/bin/python -m app.manage set-password <TG_ID>"
    echo ""
}

main() {
    log_info "=== Установка VPN Bot Panel ==="
    check_root
    install_system_packages
    check_python_version
    setup_repository
    create_venv
    install_dependencies
    run_setup
    set_permissions
    create_service
    start_service || true
    show_final_instructions
}

main "$@"
