#!/bin/bash

set -e

echo "🧹 Очистка места на диске перед установкой..."

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

check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_success "Проверка прав: root"
    else
        log_error "Требуются права root"
        log_info "Запустите: sudo $0"
        exit 1
    fi
}

show_disk_usage() {
    log_info "Текущее использование диска:"
    df -h
    echo ""
}

clean_apt_cache() {
    log_info "Очистка кэша apt..."
    apt clean
    apt autoclean
    log_success "Кэш apt очищен"
}

remove_unused_packages() {
    log_info "Удаление неиспользуемых пакетов..."
    apt autoremove --purge -y
    log_success "Неиспользуемые пакеты удалены"
}

clean_logs() {
    log_info "Очистка логов..."
    
    # Очистка journal logs
    journalctl --vacuum-time=1d 2>/dev/null || true
    
    # Очистка старых логов
    find /var/log -name "*.log" -type f -exec truncate -s 0 {} \; 2>/dev/null || true
    find /var/log -name "*.gz" -type f -delete 2>/dev/null || true
    find /var/log -name "*.1" -type f -delete 2>/dev/null || true
    
    log_success "Логи очищены"
}

clean_tmp() {
    log_info "Очистка временных файлов..."
    rm -rf /tmp/* /var/tmp/*
    log_success "Временные файлы очищены"
}

remove_old_kernels() {
    log_info "Проверка старых ядер..."
    
    if command -v dpkg > /dev/null; then
        # Получаем текущее ядро
        current_kernel=$(uname -r | sed 's/-*[a-z]//g' | sed 's/-386//g')
        
        # Удаляем старые ядра
        dpkg -l | grep 'linux-image' | awk '{print $2}' | while read kernel; do
            if [[ "$kernel" != *"$current_kernel"* ]]; then
                log_info "Удаление старого ядра: $kernel"
                apt remove --purge -y "$kernel" 2>/dev/null || true
            fi
        done
        
        # Очищаем заголовки ядер
        dpkg -l | grep 'linux-headers' | awk '{print $2}' | while read headers; do
            if [[ "$headers" != *"$current_kernel"* ]]; then
                log_info "Удаление старых заголовков: $headers"
                apt remove --purge -y "$headers" 2>/dev/null || true
            fi
        done
        
        log_success "Старые ядра удалены"
    else
        log_warning "Не удалось проверить ядра (не найден dpkg)"
    fi
}

clean_package_cache() {
    log_info "Очистка кэша пакетов..."
    
    # Очищаем списки пакетов
    rm -f /var/lib/apt/lists/* 2>/dev/null || true
    apt update
    
    log_success "Кэш пакетов очищен"
}

find_large_files() {
    log_info "Поиск больших файлов (топ 20):"
    
    # Ищем большие файлы (больше 100MB)
    find / -type f -size +100M -exec ls -lh {} \; 2>/dev/null | sort -k5 -hr | head -20 || true
    
    echo ""
    
    log_info "Поиск больших директорий в /var (топ 10):"
    du -sh /var/* 2>/dev/null | sort -hr | head -10 || true
}

check_disk_space() {
    log_info "Проверка свободного места..."
    
    local available_kb=$(df / | awk 'NR==2 {print $4}')
    local available_mb=$((available_kb / 1024))
    local available_gb=$((available_mb / 1024))
    
    local required_mb=500  # Минимум 500MB для установки
    
    if [ "$available_mb" -lt "$required_mb" ]; then
        log_error "Недостаточно свободного места!"
        log_info "Доступно: ${available_mb} MB"
        log_info "Требуется: ${required_mb} MB"
        return 1
    else
        log_success "Свободного места достаточно: ${available_gb}.${available_mb} GB"
        return 0
    fi
}

main() {
    log_info "Начало очистки системы..."
    
    check_root
    
    local initial_space=$(df / | awk 'NR==2 {print $4}')
    
    show_disk_usage
    clean_apt_cache
    remove_unused_packages
    clean_logs
    clean_tmp
    remove_old_kernels
    clean_package_cache
    
    local final_space=$(df / | awk 'NR==2 {print $4}')
    local freed_space=$((final_space - initial_space))
    local freed_mb=$((freed_space / 1024))
    
    show_disk_usage
    
    if [ "$freed_mb" -gt 0 ]; then
        log_success "Освобождено: ${freed_mb} MB"
    else
        log_warning "Не удалось освободить значительное место"
    fi
    
    if check_disk_space; then
        log_success "✅ Места достаточно для установки!"
    else
        log_error "❌ Места все еще недостаточно"
        find_large_files
        log_info "Рекомендации:"
        log_info "1. Удалите ненужные большие файлы"
        log_info "2. Увеличьте размер диска"
        log_info "3. Установите в другую директорию с большим местом"
        exit 1
    fi
}

# Обработка аргументов
case "${1:-}" in
    "check")
        check_disk_space
        ;;
    "large-files")
        find_large_files
        ;;
    "help"|"-h"|"--help")
        echo "Использование: $0 [command]"
        echo ""
        echo "Команды:"
        echo "  check       - проверить свободное место"
        echo "  large-files - найти большие файлы"
        echo "  help        - показать эту справку"
        echo ""
        echo "Без аргументов: выполнить полную очистку"
        ;;
    *)
        main
        ;;
esac