#!/bin/bash

set -e

print_color() {
    echo -e "${2}${1}\033[0m"
}

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'

PROJECT_DIR="/opt/vpnbot"
BACKUP_DIR="/opt/vpnbot_backup_$(date +%Y%m%d_%H%M%S)"
TEMP_DIR=$(mktemp -d)

echo "=================================================="
print_color " VPN Bot Update Script" "$BLUE"
echo "=================================================="

# Создание бэкапа
print_color "📦 Creating backup..." "$BLUE"
mkdir -p "$BACKUP_DIR"
cp -r $PROJECT_DIR/*.py $PROJECT_DIR/requirements.txt $PROJECT_DIR/templates "$BACKUP_DIR/" 2>/dev/null || true
print_color "✅ Backup created: $BACKUP_DIR" "$GREEN"

# Остановка служб
print_color "🛑 Stopping services..." "$BLUE"
systemctl stop vpnbot vpnbot-web

# Скачивание обновлений с GitHub
print_color "📥 Downloading updates from GitHub..." "$BLUE"
cd $TEMP_DIR
wget -q https://github.com/your_username/vpn-bot-panel/archive/main.tar.gz -O update.tar.gz
tar -xzf update.tar.gz
cd vpn-bot-panel-main

# Копирование обновленных файлов
print_color "🔄 Copying updated files..." "$BLUE"
cp -f *.py $PROJECT_DIR/
cp -f requirements.txt $PROJECT_DIR/
cp -rf templates/* $PROJECT_DIR/templates/ 2>/dev/null || true

# Установка прав
chown -R vpnbot:vpnbot $PROJECT_DIR

# Обновление зависимостей
print_color "📦 Updating dependencies..." "$BLUE"
sudo -u vpnbot $PROJECT_DIR/venv/bin/pip install --upgrade pip
sudo -u vpnbot $PROJECT_DIR/venv/bin/pip install -r $PROJECT_DIR/requirements.txt

# Обновление базы данных если нужно
print_color "🗃️ Updating database..." "$BLUE"
sudo -u vpnbot $PROJECT_DIR/venv/bin/python3 -c "
import sys
sys.path.append('/opt/vpnbot')
from database import init_db
init_db()
print('Database updated')
"

# Запуск служб
print_color "🚀 Starting services..." "$BLUE"
systemctl start vpnbot vpnbot-web

# Очистка временных файлов
rm -rf $TEMP_DIR

# Проверка статуса
sleep 3
print_color "🔍 Checking service status..." "$BLUE"
systemctl is-active vpnbot && print_color "✅ Bot service running" "$GREEN" || print_color "❌ Bot service failed" "$RED"
systemctl is-active vpnbot-web && print_color "✅ Web panel service running" "$GREEN" || print_color "❌ Web panel service failed" "$RED"

print_color "✅ Update completed successfully!" "$GREEN"
