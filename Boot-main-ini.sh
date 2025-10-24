# В раздел функций меню добавьте:

admin_panel_control() {
    log_header "Управление админ-панелью"
    
    echo -e "\n${YELLOW}Статус админ-панели:${NC}"
    if systemctl is-active --quiet vpn-admin-panel.service; then
        echo -e "   Статус: ${GREEN}запущена${NC}"
    else
        echo -e "   Статус: ${RED}остановлена${NC}"
    fi
    
    load_panel_config
    echo -e "   Порт: $PANEL_PORT"
    echo -e "   URL: $PANEL_URL"
    
    echo -e "\n${YELLOW}Действия:${NC}"
    echo "1. Запустить админ-панель"
    echo "2. Остановить админ-панель" 
    echo "3. Перезапустить админ-панель"
    echo "4. Показать статус"
    echo "5. Показать логи"
    echo "0. Назад"
    
    read -p "Выберите действие (0-5): " action
    
    case $action in
        1) start_admin_panel ;;
        2) stop_admin_panel ;;
        3) restart_admin_panel ;;
        4) show_admin_panel_status ;;
        5) show_admin_panel_logs ;;
        0) main_menu ;;
        *) log_error "Неверный выбор"; admin_panel_control ;;
    esac
}

start_admin_panel() {
    log_info "Запуск админ-панели..."
    if systemctl start vpn-admin-panel.service; then
        log_success "Админ-панель запущена"
        # Включение в конфиге
        PANEL_ENABLED=true
        save_panel_config
    else
        log_error "Не удалось запустить админ-панель"
    fi
    sleep 2
    admin_panel_control
}

stop_admin_panel() {
    log_info "Остановка админ-панели..."
    if systemctl stop vpn-admin-panel.service; then
        log_success "Админ-панель остановлена"
        # Выключение в конфиге
        PANEL_ENABLED=false
        save_panel_config
    else
        log_error "Не удалось остановить админ-панель"
    fi
    sleep 2
    admin_panel_control
}

restart_admin_panel() {
    log_info "Перезапуск админ-панели..."
    if systemctl restart vpn-admin-panel.service; then
        log_success "Админ-панель перезапущена"
    else
        log_error "Не удалось перезапустить админ-панель"
    fi
    sleep 2
    admin_panel_control
}

show_admin_panel_status() {
    log_header "Статус админ-панели"
    systemctl status vpn-admin-panel.service --no-pager -l
    read -p "Нажмите Enter для продолжения..."
    admin_panel_control
}

show_admin_panel_logs() {
    log_header "Логи админ-панели"
    if [ -f "logs/admin-panel.log" ]; then
        tail -50 logs/admin-panel.log
    else
        log_error "Файл логов не найден"
    fi
    read -p "Нажмите Enter для продолжения..."
    admin_panel_control
}