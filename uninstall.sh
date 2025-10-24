#!/bin/bash

# VPN Bot Panel - Скрипт удаления
set -e

echo "🧹 Запуск удаления VPN Bot Panel..."

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

# Подтверждение удаления
confirm_uninstall() {
    echo ""
    log_warning "⚠️  ВНИМАНИЕ: Это навсегда удалит:"
    echo "   - Виртуальное окружение (venv/)"
    echo "   - Базу данных и все данные (data/)"
    echo "   - Файлы конфигурации (config.ini, panel_config.json)"
    echo "   - Файлы логов (logs/)"
    echo "   - VPN конфигурации"
    echo "   - Systemd сервис"
    echo ""
    echo "Это действие нельзя отменить!"
    echo ""
    
    read -p "Вы уверены, что хотите продолжить? (введите 'УДАЛИТЬ' для подтверждения): " -r
    echo
    if [[ ! $REPLY == "УДАЛИТЬ" ]]; then
        log_info "Удаление отменено."
        exit 0
    fi
}

# Резервное копирование важных данных
backup_data() {
    local backup_dir="backup_$(date +%Y%m%d_%H%M%S)"
    
    log_info "Создание резервной копии важных данных..."
    mkdir -p "$backup_dir"
    
    # Резервное копирование базы данных если существует
    if [ -f "data/vpn_bot.db" ]; then
        cp "data/vpn_bot.db" "$backup_dir/" 2>/dev/null && log_success "База данных скопирована" || log_warning "Не удалось скопировать базу данных"
    fi
    
    # Резервное копирование конфигурации если существует
    if [ -f "config.ini" ]; then
        cp "config.ini" "$backup_dir/" 2>/dev/null && log_success "Конфигурация скопирована" || log_warning "Не удалось скопировать конфигурацию"
    fi
    
    # Резервное копирование panel_config.json если существует
    if [ -f "panel_config.json" ]; then
        cp "panel_config.json" "$backup_dir/" 2>/dev/null && log_success "Конфигурация панели скопирована" || log_warning "Не удалось скопировать конфигурацию панели"
    fi
    
    # Резервное копирование учетных данных администраторов если возможно
    if command -v sqlite3 >/dev/null 2>&1 && [ -f "data/vpn_bot.db" ]; then
        sqlite3 data/vpn_bot.db "SELECT username, telegram_id, full_name FROM admins;" > "$backup_dir/admins.txt" 2>/dev/null && log_success "Список администраторов скопирован" || log_warning "Не удалось скопировать список администраторов"
    fi
    
    if [ -d "$backup_dir" ] && [ "$(ls -A "$backup_dir")" ]; then
        tar -czf "${backup_dir}.tar.gz" "$backup_dir" 2>/dev/null && log_success "Резервная копия сохранена как ${backup_dir}.tar.gz" || log_warning "Не удалось сжать резервную копию"
        rm -rf "$backup_dir"
    else
        rm -rf "$backup_dir"
        log_info "Нет данных для резервного копирования"
    fi
}

# Остановка и удаление systemd сервиса
remove_systemd_service() {
    log_info "Остановка и удаление systemd сервиса..."
    
    if systemctl is-active --quiet vpn-bot-panel.service; then
        systemctl stop vpn-bot-panel.service
        log_success "Сервис остановлен"
    fi
    
    if systemctl is-enabled --quiet vpn-bot-panel.service; then
        systemctl disable vpn-bot-panel.service
        log_success "Сервис отключен"
    fi
    
    if [ -f "/etc/systemd/system/vpn-bot-panel.service" ]; then
        rm -f "/etc/systemd/system/vpn-bot-panel.service"
        systemctl daemon-reload
        log_success "Файл сервиса удален"
    fi
}

# Удаление виртуального окружения
remove_venv() {
    if [ -d "venv" ]; then
        log_info "Удаление виртуального окружения..."
        rm -rf venv
        log_success "Виртуальное окружение удалено"
    else
        log_info "Виртуальное окружение не найдено"
    fi
}

# Удаление директорий данных
remove_data_dirs() {
    local dirs=("data" "logs" "backups")
    
    for dir in "${dirs[@]}"; do
        if [ -d "$dir" ]; then
            log_info "Удаление директории $dir/ ..."
            rm -rf "$dir"
            log_success "Директория $dir/ удалена"
        else
            log_info "Директория $dir/ не найдена"
        fi
    done
}

# Удаление файлов конфигурации
remove_config_files() {
    local files=("config.ini" "panel_config.json" ".env" ".env.local")
    
    for file in "${files[@]}"; do
        if [ -f "$file" ]; then
            log_info "Удаление $file..."
            rm -f "$file"
            log_success "$file удален"
        else
            log_info "$file не найден"
        fi
    done
}

# Удаление сгенерированных VPN конфигураций
remove_vpn_configs() {
    if [ -d "vpn_configs" ]; then
        log_info "Удаление сгенерированных VPN конфигураций..."
        rm -rf vpn_configs
        log_success "VPN конфигурации удалены"
    fi
}

# Очистка кэша Python
clean_python_cache() {
    log_info "Очистка кэш-файлов Python..."
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    find . -type f -name "*.pyo" -delete 2>/dev/null || true
    find . -type f -name ".coverage" -delete 2>/dev/null || true
    find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
    log_success "Кэш Python очищен"
}

# Удаление исполняемых скриптов
remove_scripts() {
    log_info "Удаление исполняемых скриптов..."
    rm -f Boot-main-ini 2>/dev/null || true
    log_success "Скрипты удалены"
}

# Показать заключительное сообщение
show_final_message() {
    echo ""
    log_success "🎉 Удаление завершено успешно!"
    echo ""
    log_info "Были удалены:"
    echo "   ✅ Виртуальное окружение"
    echo "   ✅ База данных и пользовательские данные"
    echo "   ✅ Файлы конфигурации"
    echo "   ✅ Файлы логов"
    echo "   ✅ VPN конфигурации"
    echo "   ✅ Systemd сервис"
    echo "   ✅ Кэш-файлы Python"
    echo ""
    log_info "Резервная копия была создана в текущей директории если какие-либо данные существовали."
    echo ""
    log_info "Спасибо за использование VPN Bot Panel!"
    echo ""
}

# Главный процесс удаления
main() {
    log_info "Начало процесса удаления VPN Bot Panel..."
    
    # Проверка если мы в директории проекта
    check_project_dir
    
    # Проверка прав
    check_root
    
    # Подтверждение удаления
    confirm_uninstall
    
    # Резервное копирование важных данных
    backup_data
    
    # Остановка сервисов
    remove_systemd_service
    
    # Удаление компонентов
    remove_venv
    remove_data_dirs
    remove_config_files
    remove_vpn_configs
    remove_scripts
    clean_python_cache
    
    # Заключительное сообщение
    show_final_message
}

# Запуск главной функции
main "$@"