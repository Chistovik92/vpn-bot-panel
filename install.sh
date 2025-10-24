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

# Проверка установки Git
check_git() {
    if ! command -v git &>/dev/null; then
        log_error "Git не установлен. Установите Git сначала:"
        log_info "Ubuntu/Debian: sudo apt-get install git"
        log_info "CentOS/RHEL: sudo yum install git"
        exit 1
    fi
    log_success "Git найден: $(git --version)"
}

# Проверка установки jq
check_jq() {
    if ! command -v jq &>/dev/null; then
        log_info "Установка jq для работы с JSON..."
        if command -v apt-get &>/dev/null; then
            apt-get update && apt-get install -y jq
        elif command -v yum &>/dev/null; then
            yum install -y jq
        else
            log_error "Не удалось установить jq. Установите его вручную."
            exit 1
        fi
    fi
    log_success "jq установлен"
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
        $PYTHON_CMD -m venv venv
        log_success "Виртуальное окружение создано"
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

# Создание systemd сервиса
create_systemd_service() {
    log_info "Создание systemd сервиса..."
    
    local service_file="/etc/systemd/system/vpn-bot-panel.service"
    
    cat > $service_file << EOF
[Unit]
Description=VPN Bot Panel
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/venv/bin/python bot.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable vpn-bot-panel.service
    log_success "Systemd сервис создан и включен"
}

# Показать заключительные инструкции
show_final_instructions() {
    local panel_url="http://localhost:5000"
    
    # Загрузка конфигурации если существует
    if [ -f "panel_config.json" ]; then
        panel_url=$(jq -r '.admin_panel_url // "http://localhost:5000"' panel_config.json)
    fi
    
    echo ""
    log_success "🎉 Установка завершена успешно!"
    echo ""
    echo "📝 Следующие шаги:"
    echo "   1. Настройте параметры в config.ini"
    echo "   2. Запустите бота: ./Boot-main-ini (выберите пункт 1)"
    echo "   3. Доступ к админ панели: $panel_url"
    echo ""
    echo "🔐 Рекомендации по безопасности:"
    echo "   - Регулярно меняйте пароли по умолчанию"
    echo "   - Обновляйте сервер регулярно"
    echo "   - Мониторьте логи на подозрительную активность"
    echo "   - Регулярно делайте резервные копии базы данных"
    echo ""
    echo "💡 Советы:"
    echo "   - Используйте ./Boot-main-ini для управления системой"
    echo "   - Проверьте README.md для подробных инструкций"
    echo "   - Логи находятся в директории logs/"
    echo ""
}

# Главный процесс установки
main() {
    log_info "Начало установки VPN Bot Panel..."
    
    # Проверка прав
    check_root
    
    # Проверка платформы
    check_platform
    
    # Проверка и настройка репозитория
    check_git
    check_jq
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
    
    # Создание systemd сервиса
    create_systemd_service
    
    # Показать заключительные инструкции
    show_final_instructions
}

# Запуск главной функции
main "$@"