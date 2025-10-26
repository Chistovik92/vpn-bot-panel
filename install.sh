#!/bin/bash

set -e

echo "🚀 Установщик VPN Bot Panel"
echo "📦 Загрузка и запуск основного скрипта установки..."

# Временная директория
TEMP_DIR="/tmp/vpn-bot-install"
mkdir -p "$TEMP_DIR"

# Скачиваем скрипт установки из папки scripts
curl -sSL https://raw.githubusercontent.com/Chistovik92/vpn-bot-panel/Dev_Bot-plan/scripts/install.sh -o "$TEMP_DIR/install-main.sh"

if [ $? -eq 0 ]; then
    chmod +x "$TEMP_DIR/install-main.sh"
    echo "✅ Скрипт установки загружен"
    echo "🔄 Запуск установки..."
    bash "$TEMP_DIR/install-main.sh" "$@"
    rm -rf "$TEMP_DIR"
else
    echo "❌ Ошибка загрузки скрипта установки"
    echo ""
    echo "Альтернативные способы установки:"
    echo "1. Клонировать репозиторий:"
    echo "   git clone https://github.com/Chistovik92/vpn-bot-panel.git"
    echo "   cd vpn-bot-panel && sudo ./scripts/install.sh"
    echo ""
    echo "2. Скачать скрипт напрямую:"
    echo "   curl -sSL https://raw.githubusercontent.com/Chistovik92/vpn-bot-panel/Dev_Bot-plan/scripts/install.sh | sudo bash"
    exit 1
fi