#!/bin/bash

# VPN Bot Panel - Скрипт обновления
set -e

echo "🔄 Запуск обновления VPN Bot Panel..."

# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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
    if [[ $EUID -ne 0 ]]; then
        log_error "Этот скрипт требует прав root для выполнения"
        log_info "Запустите скрипт с помощью: sudo $0"
        exit 1
    fi
}

# Проверка директории проекта
check_project_dir() {
    if [ ! -f "install.py" ] && [ ! -f "database.py" ]; then
        log_error "Не в директории VPN Bot Panel."
        log_info "Пожалуйста, запустите этот скрипт из директории проекта."
        exit 1
    fi
}

# Создание резервной копии перед обновлением
create_backup() {
    log_info "Создание резервной копии перед обновлением..."
    local backup_dir="backups/update_backup_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"
    
    if [ -f "data/vpn_bot.db" ]; then
        cp "data/vpn_bot.db" "$backup_dir/" && log_success "База данных скопирована"
    fi
    
    if [ -f "config.ini" ]; then
        cp "config.ini" "$backup_dir/" && log_success "Конфигурация скопирована"
    fi
    
    if [ -f "panel_config.json" ]; then
        cp "panel_config.json" "$backup_dir/" && log_success "Конфигурация панели скопирована"
    fi
    
    log_success "Резервная копия создана в $backup_dir"
}

# Остановка сервисов
stop_services() {
    log_info "Остановка сервисов..."
    
    if systemctl is-active --quiet vpn-bot-panel.service; then
        systemctl stop vpn-bot-panel.service
        log_success "Сервис бота остановлен"
    fi
    
    # Остановка процессов Python бота
    pkill -f "python bot.py" 2>/dev/null && log_success "Процессы бота остановлены" || log_info "Процессы бота не запущены"
}

# Обновление кода
update_code() {
    log_info "Обновление кода из репозитория..."
    
    if git pull origin main; then
        log_success "Код успешно обновлен"
    else
        log_error "Ошибка при обновлении кода"
        exit 1
    fi
}

# Обновление зависимостей
update_dependencies() {
    log_info "Обновление зависимостей..."
    
    if [ -d "venv" ]; then
        source venv/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt
        log_success "Зависимости обновлены"
    else
        log_error "Виртуальное окружение не найдено"
        exit 1
    fi
}

# Обновление базы данных
update_database() {
    log_info "Обновление базы данных..."
    
    if [ -d "venv" ]; then
        source venv/bin/activate
        python -c "from database import Database; db = Database(); db.init_db()"
        log_success "База данных обновлена"
    else
        log_error "Виртуальное окружение не найдено"
        exit 1
    fi
}

# Обновление прав доступа
update_permissions() {
    log_info "Обновление прав доступа..."
    
    chmod +x Boot-main-ini 2>/dev/null || true
    chmod +x *.py 2>/dev/null || true
    
    if [ -f "config.ini" ]; then
        chmod 600 config.ini
    fi
    
    if [ -f "data/vpn_bot.db" ]; then
        chmod 600 data/vpn_bot.db
    fi
    
    log_success "Права доступа обновлены"
}

# Перезапуск сервисов
restart_services() {
    log_info "Перезапуск сервисов..."
    
    if systemctl start vpn-bot-panel.service; then
        log_success "Сервис бота запущен"
    else
        log_warning "Не удалось запустить systemd сервис, запуск вручную..."
        source venv/bin/activate
        nohup python bot.py > logs/bot.log 2>&1 &
        log_success "Бот запущен вручную"
    fi
}

# Показать заключительную информацию
show_final_info() {
    echo ""
    log_success "🎉 Обновление завершено успешно!"
    echo ""
    log_info "Обновленные компоненты:"
    echo "   ✅ Код приложения"
    echo "   ✅ Зависимости Python"
    echo "   ✅ Структура базы данных"
    echo "   ✅ Права доступа к файлам"
    echo ""
    log_info "Статус сервисов:"
    if systemctl is-active --quiet vpn-bot-panel.service; then
        echo "   Бот: запущен"
    else
        echo "   Бот: остановлен"
    fi
    echo ""
    log_info "Резервная копия создана в директории backups/"
    echo ""
}

# Главный процесс обновления
main() {
    log_info "Начало процесса обновления VPN Bot Panel..."
    
    # Проверка директории проекта
    check_project_dir
    
    # Проверка прав
    check_root
    
    # Создание резервной копии
    create_backup
    
    # Остановка сервисов
    stop_services
    
    # Обновление кода
    update_code
    
    # Обновление зависимостей
    update_dependencies
    
    # Обновление базы данных
    update_database
    
    # Обновление прав доступа
    update_permissions
    
    # Перезапуск сервисов
    restart_services
    
    # Заключительная информация
    show_final_info
}

# Запуск главной функции
main "$@"