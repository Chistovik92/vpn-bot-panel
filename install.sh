#!/bin/bash

# VPN Bot Panel - Скрипт установки
set -e

echo "🚀 Запуск установки VPN Bot Panel..."

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функции логирования
log_info() {
    echo -e "${BLUE}ℹ️ $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Проверка прав root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_success "Проверка прав: root доступ подтвержден"
    else
        log_error "Этот скрипт требует прав root для выполнения"
        log_info "Запустите скрипт с помощью: sudo $0"
        exit 1
    fi
}

# Проверка платформы
check_platform() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        log_success "Платформа: Linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        log_error "macOS не поддерживается"
        exit 1
    elif [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        log_error "Windows не поддерживается этим скриптом"
        log_info "Для Windows используйте install.bat"
        exit 1
    else
        log_warning "Неизвестная платформа: $OSTYPE"
    fi
}

# Проверка и установка системных пакетов
install_system_packages() {
    log_info "Проверка и установка системных пакетов..."
    
    # Определение дистрибутива
    if [ -f /etc/os-release ]; then
        source /etc/os-release
        case $ID in
            debian|ubuntu)
                log_info "Обнаружен Debian/Ubuntu, установка пакетов..."
                apt update
                apt install -y python3-venv python3-pip git jq curl
                ;;
            centos|rhel|fedora)
                log_info "Обнаружен CentOS/RHEL/Fedora, установка пакетов..."
                if command -v dnf >/dev/null 2>&1; then
                    dnf install -y python3-virtualenv python3-pip git jq curl
                else
                    yum install -y python3-virtualenv python3-pip git jq curl
                fi
                ;;
            arch|manjaro)
                log_info "Обнаружен Arch/Manjaro, установка пакетов..."
                pacman -Sy --noconfirm python python-pip git jq curl
                ;;
            *)
                log_error "Неизвестный дистрибутив: $ID"
                log_info "Установите вручную: python3-venv (или python3-virtualenv), python3-pip, git, jq, curl"
                exit 1
                ;;
        esac
    else
        log_error "Не удалось определить дистрибутив Linux"
        log_info "Установите вручную: python3-venv (или python3-virtualenv), python3-pip, git, jq, curl"
        exit 1
    fi
    
    log_success "Системные пакеты установлены"
}

# Проверка установки Git
check_git() {
    if ! command -v git &>/dev/null; then
        log_error "Git не установлен"
        return 1
    fi
    log_success "Git найден: $(git --version)"
    return 0
}

# Проверка установки jq
check_jq() {
    if ! command -v jq &>/dev/null; then
        log_error "jq не установлен"
        return 1
    fi
    log_success "jq установлен"
    return 0
}

# Клонирование или обновление репозитория
setup_repository() {
    local repo_url="https://github.com/Chistovik92/vpn-bot-panel.git"
    local project_dir="vpn-bot-panel"
    
    if [ -d "$project_dir" ]; then
        log_info "Директория проекта уже существует, обновление..."
        cd "$project_dir"
        git pull origin main
        log_success "Репозиторий обновлен"
    else
        log_info "Клонирование репозитория из $repo_url..."
        git clone "$repo_url" "$project_dir"
        cd "$project_dir"
        log_success "Репозиторий успешно клонирован"
    fi
    
    # Показать текущую директорию и файлы
    log_info "Текущая директория: $(pwd)"
    log_info "Файлы в директории:"
    ls -la
}

# Проверка установки Python
check_python() {
    log_info "Проверка установки Python..."
    if command -v python3 &>/dev/null; then
        PYTHON_CMD="python3"
        log_success "Python 3 найден: $(python3 --version)"
    elif command -v python &>/dev/null; then
        PYTHON_VERSION=$(python --version 2>&1)
        if [[ $PYTHON_VERSION == *"Python 3"* ]]; then
            PYTHON_CMD="python"
            log_success "Python найден: $PYTHON_VERSION"
        else
            log_error "Требуется Python 3.8 или выше, но не найден."
            exit 1
        fi
    else
        log_error "Python не установлен. Установите Python 3.8 или выше."
        exit 1
    fi
}

# Проверка версии Python
check_python_version() {
    log_info "Проверка версии Python..."
    PYTHON_VERSION=$($PYTHON_CMD -c "import sys; print('.'.join(map(str, sys.version_info[:3])))")
    REQUIRED_VERSION="3.8"
    
    $PYTHON_CMD -c "import sys; exit(0) if tuple(map(int, sys.version_info[:2])) >= tuple(map(int, '$REQUIRED_VERSION'.split('.'))) else exit(1)"
    
    if [ $? -eq 0 ]; then
        log_success "Версия Python $PYTHON_VERSION совместима"
    else
        log_error "Требуется Python $REQUIRED_VERSION или выше. Текущая версия: $PYTHON_VERSION"
        exit 1
    fi
}

# Проверка существования необходимых файлов
check_required_files() {
    log_info "Проверка необходимых файлов..."
    
    local required_files=("install.py" "database.py" "config.py" "requirements.txt")
    local missing_files=()
    
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            missing_files+=("$file")
        fi
    done
    
    if [ ${#missing_files[@]} -ne 0 ]; then
        log_error "Отсутствуют необходимые файлы: ${missing_files[*]}"
        return 1
    fi
    
    log_success "Все необходимые файлы найдены"
    return 0
}

# Создание виртуального окружения
create_venv() {
    log_info "Создание виртуального окружения Python..."
    
    if [ ! -d "venv" ]; then
        # Попытка создать виртуальное окружение
        if $PYTHON_CMD -m venv venv 2>/dev/null; then
            log_success "Виртуальное окружение создано"
        else
            log_error "Не удалось создать виртуальное окружение"
            log_info "Попытка установить необходимые пакеты..."
            install_system_packages
            
            # Повторная попытка после установки пакетов
            log_info "Повторная попытка создания виртуального окружения..."
            if $PYTHON_CMD -m venv venv; then
                log_success "Виртуальное окружение создано после установки пакетов"
            else
                log_error "Не удалось создать виртуальное окружение даже после установки пакетов"
                log_info "Попробуйте установить вручную:"
                log_info "Ubuntu/Debian: sudo apt install python3-venv"
                log_info "CentOS/RHEL: sudo yum install python3-virtualenv"
                exit 1
            fi
        fi
    else
        log_info "Виртуальное окружение уже существует"
    fi
}

# Активация виртуального окружения
activate_venv() {
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
        PYTHON_CMD="venv/bin/python"
        log_success "Виртуальное окружение активировано"
    elif [ -f "venv/Scripts/activate" ]; then
        source venv/Scripts/activate
        PYTHON_CMD="venv/Scripts/python"
        log_success "Виртуальное окружение активировано"
    else
        log_warning "Не удалось активировать виртуальное окружение, используется системный Python"
    fi
}

# Установка зависимостей
install_dependencies() {
    log_info "Установка зависимостей..."
    
    # Обновление pip сначала
    log_info "Обновление pip..."
    if ! $PYTHON_CMD -m pip install --upgrade pip; then
        log_warning "Не удалось обновить pip, продолжение с текущей версией..."
    fi
    
    # Установка требований
    if [ -f "requirements.txt" ]; then
        log_info "Установка из requirements.txt..."
        if $PYTHON_CMD -m pip install -r requirements.txt; then
            log_success "Зависимости успешно установлены"
        else
            log_error "Не удалось установить некоторые зависимости"
            log_info "Попытка установки пакетов по одному..."
            
            # Попробовать установить пакеты по одному
            packages=(
                "python-telegram-bot==20.7"
                "yookassa==3.7.1" 
                "aiohttp==3.9.1"
                "cryptography==41.0.7"
                "sqlalchemy==2.0.23"
                "flask==2.3.3"
            )
            
            for package in "${packages[@]}"; do
                log_info "Установка $package..."
                if $PYTHON_CMD -m pip install "$package"; then
                    log_success "Установлен $package"
                else
                    log_warning "Не удалось установить $package"
                fi
            done
        fi
    else
        log_error "requirements.txt не найден"
        exit 1
    fi
}

# Запуск скрипта установки
run_installation() {
    log_info "Запуск скрипта установки..."
    
    # Установка PYTHONPATH в текущую директорию
    export PYTHONPATH=$(pwd):$PYTHONPATH
    
    if $PYTHON_CMD install.py; then
        log_success "Установка завершена успешно"
    else
        log_error "Ошибка установки"
        exit 1
    fi
}

# Настройка прав доступа
set_permissions() {
    log_info "Настройка прав доступа к файлам..."
    
    # Сделать Python скрипты исполняемыми
    chmod +x *.py 2>/dev/null || true
    
    # Сделать главный скрипт исполняемым
    chmod +x Boot-main-ini 2>/dev/null || true
    
    # Убедиться, что директории данных доступны для записи с безопасными правами
    mkdir -p data/vpn_configs data/backups logs
    chmod 755 data data/vpn_configs data/backups logs
    
    # Установить безопасные права для чувствительных файлов
    if [ -f "config.ini" ]; then
        chmod 600 config.ini
    fi
    
    if [ -f "data/vpn_bot.db" ]; then
        chmod 600 data/vpn_bot.db
    fi
    
    if [ -f "panel_config.json" ]; then
        chmod 600 panel_config.json
    fi
    
    log_success "Права доступа настроены"
}

# Создание systemd сервиса для бота
create_bot_service() {
    log_info "Создание systemd сервиса для бота..."
    
    local service_file="/etc/systemd/system/vpn-bot-panel.service"
    local working_dir=$(pwd)
    
    cat > "$service_file" << EOF
[Unit]
Description=VPN Bot Panel
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$working_dir
ExecStart=$working_dir/venv/bin/python bot.py
Restart=always
RestartSec=3
StandardOutput=file:$working_dir/logs/bot.log
StandardError=file:$working_dir/logs/bot-error.log

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable vpn-bot-panel.service
    log_success "Systemd сервис для бота создан и включен"
}

# Создание systemd сервиса для админ-панели
create_admin_panel_service() {
    log_info "Создание systemd сервиса для админ-панели..."
    
    local service_file="/etc/systemd/system/vpn-admin-panel.service"
    local working_dir=$(pwd)
    
    # Загрузка конфигурации порта
    local panel_port=5000
    if [ -f "panel_config.json" ]; then
        panel_port=$(jq -r '.admin_panel_port // 5000' panel_config.json)
    fi
    
    cat > "$service_file" << EOF
[Unit]
Description=VPN Admin Panel
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$working_dir
ExecStart=$working_dir/venv/bin/python admin_panel.py
Restart=always
RestartSec=3
StandardOutput=file:$working_dir/logs/admin-panel.log
StandardError=file:$working_dir/logs/admin-panel-error.log

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable vpn-admin-panel.service
    log_success "Systemd сервис для админ-панели создан и включен"
}

# Запуск сервисов
start_services() {
    log_info "Запуск сервисов..."
    
    # Загрузка конфигурации панели
    local panel_port=5000
    local panel_enabled=true
    if [ -f "panel_config.json" ]; then
        panel_port=$(jq -r '.admin_panel_port // 5000' panel_config.json)
        panel_enabled=$(jq -r '.admin_panel_enabled // true' panel_config.json)
    fi
    
    # Запуск бота
    if systemctl start vpn-bot-panel.service; then
        log_success "Сервис бота запущен"
    else
        log_error "Не удалось запустить сервис бота"
    fi
    
    # Запуск админ-панели если включена
    if [ "$panel_enabled" = "true" ]; then
        if systemctl start vpn-admin-panel.service; then
            log_success "Сервис админ-панели запущен"
        else
            log_error "Не удалось запустить сервис админ-панели"
        fi
    else
        log_info "Админ-панель отключена в настройках"
    fi
    
    sleep 2
    
    # Проверка статуса сервисов
    log_info "Проверка статуса сервисов:"
    if systemctl is-active --quiet vpn-bot-panel.service; then
        log_success "Бот: запущен"
    else
        log_error "Бот: не запущен"
    fi
    
    if [ "$panel_enabled" = "true" ]; then
        if systemctl is-active --quiet vpn-admin-panel.service; then
            log_success "Админ-панель: запущена на порту $panel_port"
        else
            log_error "Админ-панель: не запущена"
        fi
    fi
}

# Показать заключительные инструкции
show_final_instructions() {
    local panel_port=5000
    local panel_url="http://localhost:5000"
    
    # Загрузка конфигурации если существует
    if [ -f "panel_config.json" ]; then
        panel_port=$(jq -r '.admin_panel_port // 5000' panel_config.json)
        panel_url=$(jq -r '.admin_panel_url // "http://localhost:5000"' panel_config.json)
    fi
    
    # Получение IP адреса сервера
    local server_ip=$(curl -s http://checkip.amazonaws.com || echo "localhost")
    
    echo ""
    log_success "🎉 Установка завершена успешно!"
    echo ""
    echo "📝 Следующие шаги:"
    echo "   1. Настройте параметры в config.ini"
    echo "   2. Управление системой: sudo ./Boot-main-ini"
    echo "   3. Доступ к админ панели: $panel_url"
    echo "   4. Внешний доступ: http://$server_ip:$panel_port"
    echo ""
    echo "🔐 Рекомендации по безопасности:"
    echo "   - Регулярно меняйте пароли по умолчанию"
    echo "   - Обновляйте сервер регулярно"
    echo "   - Мониторьте логи на подозрительную активность"
    echo "   - Регулярно делайте резервные копии базы данных"
    echo ""
    echo "💡 Советы:"
    echo "   - Используйте sudo ./Boot-main-ini для управления системой"
    echo "   - Проверьте README.md для подробных инструкций"
    echo "   - Логи находятся в директории logs/"
    echo "   - Автозапуск через systemd: systemctl start vpn-bot-panel"
    echo ""
    
    # Показать созданные учетные данные если есть
    if [ -f "install_credentials.txt" ]; then
        echo "🔑 Созданные учетные данные:"
        cat install_credentials.txt
        echo ""
        log_warning "⚠️  Сохраните эти учетные данные в безопасном месте!"
        echo ""
    fi
}

# Главный процесс установки
main() {
    log_info "Начало установки VPN Bot Panel..."
    
    # Проверка прав
    check_root
    
    # Проверка платформы
    check_platform
    
    # Установка системных пакетов (включая python3-venv)
    install_system_packages
    
    # Проверка и настройка репозитория
    if ! check_git; then
        log_error "Git не установлен. Установка прервана."
        exit 1
    fi
    
    if ! check_jq; then
        log_error "jq не установлен. Установка прервана."
        exit 1
    fi
    
    setup_repository
    
    # Проверка необходимых файлов
    if ! check_required_files; then
        log_error "Необходимые файлы отсутствуют даже после клонирования репозитория."
        log_info "Пожалуйста, проверьте структуру репозитория и попробуйте снова."
        exit 1
    fi
    
    # Проверка Python
    check_python
    check_python_version
    
    # Создание и активация виртуального окружения
    create_venv
    activate_venv
    
    # Установка зависимостей
    install_dependencies
    
    # Запуск установки
    run_installation
    
    # Настройка прав доступа
    set_permissions
    
    # Создание systemd сервисов
    create_bot_service
    create_admin_panel_service
    
    # Запуск сервисов
    start_services
    
    # Показать заключительные инструкции
    show_final_instructions
}

# Запуск главной функции
main "$@"