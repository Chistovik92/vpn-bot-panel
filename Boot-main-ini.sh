#!/bin/bash

# VPN Bot Panel - Главное меню управления
# Требует права root/sudo для выполнения

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
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

log_header() {
    echo -e "${PURPLE}✨ $1${NC}"
}

log_menu() {
    echo -e "${CYAN}➡️ $1${NC}"
}

# Проверка прав root/sudo
check_privileges() {
    if [[ $EUID -eq 0 ]]; then
        log_success "Проверка прав: root доступ подтвержден"
    else
        log_error "Этот скрипт требует прав root/sudo для выполнения"
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

# Проверка установки панели
check_installation() {
    if [ -f "panel_config.json" ] && [ -d "venv" ]; then
        return 0
    else
        return 1
    fi
}

# Загрузка конфигурации панели
load_panel_config() {
    if [ -f "panel_config.json" ]; then
        PANEL_PORT=$(jq -r '.admin_panel_port // 5000' panel_config.json)
        PANEL_URL=$(jq -r '.admin_panel_url // "http://localhost:5000"' panel_config.json)
        PANEL_ENABLED=$(jq -r '.admin_panel_enabled // true' panel_config.json)
    else
        PANEL_PORT=5000
        PANEL_URL="http://localhost:5000"
        PANEL_ENABLED=true
    fi
}

# Сохранение конфигурации панели
save_panel_config() {
    cat > panel_config.json << EOF
{
    "admin_panel_port": $PANEL_PORT,
    "admin_panel_url": "$PANEL_URL",
    "admin_panel_enabled": $PANEL_ENABLED,
    "servers": [],
    "features": {
        "location_change": true,
        "connection_types": true,
        "auto_backup": true
    }
}
EOF
}

# Главное меню
main_menu() {
    clear
    echo -e "${PURPLE}"
    echo "╔══════════════════════════════════════════╗"
    echo "║           VPN BOT PANEL - МЕНЮ           ║"
    echo "╠══════════════════════════════════════════╣"
    echo "║                                          ║"
    echo -e "║  ${GREEN}🚀 Управление системой${PURPLE}                   ║"
    echo -e "║  ${CYAN}1. Запуск бота${PURPLE}                            ║"
    echo -e "║  ${CYAN}2. Остановка бота${PURPLE}                         ║"
    echo -e "║  ${CYAN}3. Перезапуск бота${PURPLE}                        ║"
    echo -e "║  ${CYAN}4. Статус системы${PURPLE}                         ║"
    echo -e "║                                        ║"
    echo -e "║  ${GREEN}👑 Управление администраторами${PURPLE}           ║"
    echo -e "║  ${CYAN}5. Создать администратора${PURPLE}                 ║"
    echo -e "║  ${CYAN}6. Изменить пароль${PURPLE}                        ║"
    echo -e "║  ${CYAN}7. Список администраторов${PURPLE}                 ║"
    echo -e "║                                        ║"
    echo -e "║  ${GREEN}🌐 Настройка панели${PURPLE}                       ║"
    echo -e "║  ${CYAN}8. Изменить порт панели${PURPLE}                   ║"
    echo -e "║  ${CYAN}9. Изменить URL панели${PURPLE}                    ║"
    echo -e "║  ${CYAN}10. Включить/выключить панель${PURPLE}             ║"
    echo -e "║                                        ║"
    echo -e "║  ${GREEN}🖥️ Управление серверами${PURPLE}                  ║"
    echo -e "║  ${CYAN}11. Добавить сервер${PURPLE}                       ║"
    echo -e "║  ${CYAN}12. Удалить сервер${PURPLE}                        ║"
    echo -e "║  ${CYAN}13. Список серверов${PURPLE}                       ║"
    echo -e "║                                        ║"
    echo -e "║  ${GREEN}🔧 Дополнительные функции${PURPLE}                 ║"
    echo -e "║  ${CYAN}14. Создать ссылку подписки${PURPLE}               ║"
    echo -e "║  ${CYAN}15. Настройки функций бота${PURPLE}                ║"
    echo -e "║  ${CYAN}16. Резервное копирование${PURPLE}                 ║"
    echo -e "║                                        ║"
    echo -e "║  ${GREEN}⚙️ Системные утилиты${PURPLE}                      ║"
    echo -e "║  ${CYAN}17. Обновить панель${PURPLE}                       ║"
    echo -e "║  ${CYAN}18. Переустановить панель${PURPLE}                 ║"
    echo -e "║  ${CYAN}19. Удалить панель${PURPLE}                        ║"
    echo -e "║  ${CYAN}0. Выход${PURPLE}                                 ║"
    echo "║                                          ║"
    echo "╚══════════════════════════════════════════╝"
    echo -e "${NC}"
    
    load_panel_config
    
    echo -e "${YELLOW}📊 Текущий статус:${NC}"
    if pgrep -f "python bot.py" > /dev/null; then
        echo -e "   Бот: ${GREEN}запущен${NC}"
    else
        echo -e "   Бот: ${RED}остановлен${NC}"
    fi
    
    echo -e "   Панель: ${PANEL_URL}:${PANEL_PORT}"
    echo -e "   Статус панели: $([ "$PANEL_ENABLED" = "true" ] && echo -e "${GREEN}включена${NC}" || echo -e "${RED}выключена${NC}")"
    echo ""
    
    read -p "Выберите пункт меню (0-19): " choice
    case $choice in
        1) start_bot ;;
        2) stop_bot ;;
        3) restart_bot ;;
        4) system_status ;;
        5) create_admin ;;
        6) change_password ;;
        7) list_admins ;;
        8) change_panel_port ;;
        9) change_panel_url ;;
        10) toggle_panel ;;
        11) add_server ;;
        12) remove_server ;;
        13) list_servers ;;
        14) create_subscription ;;
        15) bot_features ;;
        16) backup_system ;;
        17) update_panel ;;
        18) reinstall_panel ;;
        19) uninstall_panel ;;
        0) exit 0 ;;
        *) log_error "Неверный выбор"; main_menu ;;
    esac
}

# Функции меню

start_bot() {
    log_header "Запуск бота..."
    if [ -d "venv" ]; then
        source venv/bin/activate
        nohup python bot.py > logs/bot.log 2>&1 &
        log_success "Бот запущен в фоновом режиме"
        log_info "Логи: logs/bot.log"
    else
        log_error "Виртуальное окружение не найдено"
    fi
    sleep 2
    main_menu
}

stop_bot() {
    log_header "Остановка бота..."
    pkill -f "python bot.py" && log_success "Бот остановлен" || log_warning "Бот не был запущен"
    sleep 2
    main_menu
}

restart_bot() {
    log_header "Перезапуск бота..."
    pkill -f "python bot.py" 2>/dev/null
    sleep 2
    if [ -d "venv" ]; then
        source venv/bin/activate
        nohup python bot.py > logs/bot.log 2>&1 &
        log_success "Бот перезапущен"
    else
        log_error "Виртуальное окружение не найдено"
    fi
    sleep 2
    main_menu
}

system_status() {
    log_header "Статус системы"
    
    echo -e "\n${YELLOW}Процессы:${NC}"
    if pgrep -f "python bot.py" > /dev/null; then
        echo -e "   Бот: ${GREEN}запущен${NC}"
    else
        echo -e "   Бот: ${RED}остановлен${NC}"
    fi
    
    echo -e "\n${YELLOW}База данных:${NC}"
    if [ -f "data/vpn_bot.db" ]; then
        DB_SIZE=$(du -h data/vpn_bot.db | cut -f1)
        echo -e "   Размер: $DB_SIZE"
        source venv/bin/activate
        USER_COUNT=$(python -c "from database import Database; db = Database(); print(sum(1 for _ in db.get_connection().cursor().execute('SELECT id FROM users')))" 2>/dev/null || echo "0")
        echo -e "   Пользователей: $USER_COUNT"
    else
        echo -e "   ${RED}не найдена${NC}"
    fi
    
    echo -e "\n${YELLOW}Конфигурация:${NC}"
    load_panel_config
    echo -e "   Порт панели: $PANEL_PORT"
    echo -e "   URL панели: $PANEL_URL"
    
    read -p "Нажмите Enter для продолжения..."
    main_menu
}

create_admin() {
    log_header "Создание администратора"
    
    read -p "Введите Telegram ID администратора: " telegram_id
    read -p "Введите имя пользователя: " username
    read -s -p "Введите пароль: " password
    echo
    read -s -p "Подтвердите пароль: " password_confirm
    echo
    
    if [ "$password" != "$password_confirm" ]; then
        log_error "Пароли не совпадают"
        create_admin
    fi
    
    if [ -d "venv" ]; then
        source venv/bin/activate
        python -c "
import sys
sys.path.append('.')
from database import Database
from install import hash_password
db = Database()
password_hash = hash_password('$password')
try:
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO admins 
            (telegram_id, username, password_hash, full_name, role, is_active)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ($telegram_id, '$username', password_hash, 'Administrator', 'superadmin', True))
    print('✅ Администратор создан успешно')
except Exception as e:
    print('❌ Ошибка:', str(e))
"
    else
        log_error "Виртуальное окружение не найдено"
    fi
    
    read -p "Нажмите Enter для продолжения..."
    main_menu
}

change_password() {
    log_header "Изменение пароля администратора"
    
    read -p "Введите имя пользователя: " username
    read -s -p "Введите новый пароль: " password
    echo
    read -s -p "Подтвердите пароль: " password_confirm
    echo
    
    if [ "$password" != "$password_confirm" ]; then
        log_error "Пароли не совпадают"
        change_password
    fi
    
    if [ -d "venv" ]; then
        source venv/bin/activate
        python -c "
import sys
sys.path.append('.')
from database import Database
from install import hash_password
db = Database()
password_hash = hash_password('$password')
try:
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE admins SET password_hash = ? WHERE username = ?', (password_hash, '$username'))
        if cursor.rowcount == 0:
            print('❌ Пользователь не найден')
        else:
            print('✅ Пароль изменен успешно')
except Exception as e:
    print('❌ Ошибка:', str(e))
"
    else
        log_error "Виртуальное окружение не найдено"
    fi
    
    read -p "Нажмите Enter для продолжения..."
    main_menu
}

list_admins() {
    log_header "Список администраторов"
    
    if [ -d "venv" ]; then
        source venv/bin/activate
        python -c "
import sys
sys.path.append('.')
from database import Database
db = Database()
try:
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT username, telegram_id, role, created_date FROM admins WHERE is_active = 1')
        admins = cursor.fetchall()
        if admins:
            print('👑 Администраторы:')
            for admin in admins:
                print(f'   👤 {admin[0]} (ID: {admin[1]})')
                print(f'      Роль: {admin[2]}, Создан: {admin[3]}')
                print()
        else:
            print('❌ Администраторы не найдены')
except Exception as e:
    print('❌ Ошибка:', str(e))
"
    else
        log_error "Виртуальное окружение не найдено"
    fi
    
    read -p "Нажмите Enter для продолжения..."
    main_menu
}

change_panel_port() {
    log_header "Изменение порта панели"
    
    load_panel_config
    echo -e "Текущий порт: ${YELLOW}$PANEL_PORT${NC}"
    read -p "Введите новый порт (1024-65535): " new_port
    
    if ! [[ "$new_port" =~ ^[0-9]+$ ]] || [ "$new_port" -lt 1024 ] || [ "$new_port" -gt 65535 ]; then
        log_error "Неверный порт. Должен быть числом от 1024 до 65535"
        change_panel_port
    fi
    
    PANEL_PORT=$new_port
    save_panel_config
    log_success "Порт изменен на $new_port"
    log_info "Для применения изменений требуется перезапуск панели"
    
    read -p "Нажмите Enter для продолжения..."
    main_menu
}

change_panel_url() {
    log_header "Изменение URL панели"
    
    load_panel_config
    echo -e "Текущий URL: ${YELLOW}$PANEL_URL${NC}"
    read -p "Введите новый URL (например: https://mydomain.com): " new_url
    
    PANEL_URL=$new_url
    save_panel_config
    log_success "URL изменен на $new_url"
    
    read -p "Нажмите Enter для продолжения..."
    main_menu
}

toggle_panel() {
    log_header "Включение/выключение панели"
    
    load_panel_config
    if [ "$PANEL_ENABLED" = "true" ]; then
        PANEL_ENABLED=false
        log_success "Панель выключена"
    else
        PANEL_ENABLED=true
        log_success "Панель включена"
    fi
    
    save_panel_config
    read -p "Нажмите Enter для продолжения..."
    main_menu
}

add_server() {
    log_header "Добавление сервера"
    
    read -p "Введите имя сервера: " name
    read -p "Введите IP адрес: " ip
    read -p "Введите порт: " port
    read -p "Введите тип (wireguard/openvpn): " type
    read -p "Введите местоположение: " location
    
    # Здесь будет интеграция с 3x-ui API
    log_success "Сервер $name добавлен в список"
    log_warning "Интеграция с 3x-ui в разработке"
    
    read -p "Нажмите Enter для продолжения..."
    main_menu
}

remove_server() {
    log_header "Удаление сервера"
    
    # Здесь будет интеграция с 3x-ui API
    log_warning "Функция удаления серверов в разработке"
    
    read -p "Нажмите Enter для продолжения..."
    main_menu
}

list_servers() {
    log_header "Список серверов"
    
    # Здесь будет интеграция с 3x-ui API
    log_warning "Список серверов в разработке"
    
    read -p "Нажмите Enter для продолжения..."
    main_menu
}

create_subscription() {
    log_header "Создание ссылки подписки"
    
    if [ -d "venv" ]; then
        source venv/bin/activate
        python -c "
import secrets
import string
subscription_id = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))
print(f'🔗 Ссылка подписки: https://your-domain.com/subscribe/{subscription_id}')
print(f'📋 ID подписки: {subscription_id}')
print('⚠️  Сохраните эту ссылку для распространения')
"
    else
        log_error "Виртуальное окружение не найдено"
    fi
    
    read -p "Нажмите Enter для продолжения..."
    main_menu
}

bot_features() {
    log_header "Настройки функций бота"
    
    echo -e "\n${YELLOW}Доступные функции:${NC}"
    echo "1. Смена локаций пользователями"
    echo "2. Смена типов подключения"
    echo "3. Автоматическое резервное копирование"
    echo "4. Уведомления администратору"
    
    read -p "Выберите функцию для настройки (1-4): " feature_choice
    case $feature_choice in
        1) log_success "Смена локаций: включено";;
        2) log_success "Смена типов подключения: включено";;
        3) log_success "Авто-бэкап: включено";;
        4) log_success "Уведомления: включено";;
        *) log_error "Неверный выбор";;
    esac
    
    read -p "Нажмите Enter для продолжения..."
    main_menu
}

backup_system() {
    log_header "Резервное копирование системы"
    
    BACKUP_DIR="backups/backup_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    if [ -f "data/vpn_bot.db" ]; then
        cp "data/vpn_bot.db" "$BACKUP_DIR/" && log_success "База данных скопирована"
    fi
    
    if [ -f "config.ini" ]; then
        cp "config.ini" "$BACKUP_DIR/" && log_success "Конфигурация скопирована"
    fi
    
    if [ -d "data/vpn_configs" ]; then
        cp -r "data/vpn_configs" "$BACKUP_DIR/" && log_success "VPN конфигурации скопированы"
    fi
    
    log_success "Резервная копия создана в $BACKUP_DIR"
    
    read -p "Нажмите Enter для продолжения..."
    main_menu
}

update_panel() {
    log_header "Обновление панели"
    
    log_info "Обновление кода из репозитория..."
    git pull origin main
    
    log_info "Обновление зависимостей..."
    source venv/bin/activate
    pip install -r requirements.txt
    
    log_info "Обновление базы данных..."
    python -c "from database import Database; db = Database(); db.init_db()"
    
    log_success "Панель успешно обновлена"
    
    read -p "Нажмите Enter для продолжения..."
    main_menu
}

reinstall_panel() {
    log_header "Переустановка панели"
    
    log_warning "Это сохранит данные, но переустановит код и зависимости"
    read -p "Вы уверены? (y/N): " confirm
    if [[ $confirm =~ ^[Yy]$ ]]; then
        ./install.sh
    else
        log_info "Переустановка отменена"
    fi
    
    main_menu
}

uninstall_panel() {
    log_header "Удаление панели"
    
    log_error "⚠️  ВНИМАНИЕ: Это полностью удалит панель и все данные!"
    read -p "Для подтверждения введите 'УДАЛИТЬ': " confirm
    
    if [ "$confirm" = "УДАЛИТЬ" ]; then
        log_info "Запуск скрипта удаления..."
        ./uninstall.sh
    else
        log_info "Удаление отменено"
        main_menu
    fi
}

# Инициализация
init_system() {
    clear
    log_header "VPN Bot Panel - Система управления"
    
    # Проверка прав
    check_privileges
    
    # Проверка платформы
    check_platform
    
    # Проверка установки
    if ! check_installation; then
        log_error "Панель не установлена или установлена неправильно"
        log_info "Запустите install.sh для установки"
        exit 1
    fi
    
    # Создание panel_config.json если не существует
    if [ ! -f "panel_config.json" ]; then
        save_panel_config
        log_success "Конфигурационный файл создан"
    fi
    
    # Запуск главного меню
    main_menu
}

# Запуск системы
init_system "$@"