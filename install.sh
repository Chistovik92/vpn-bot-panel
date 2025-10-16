
### 2. install.sh

```bash
#!/bin/bash

set -e

echo "=================================================="
echo " VPN Bot & Web Panel Installation Script"
echo "=================================================="

# GitHub репозиторий
GITHUB_REPO="your_username/vpn-bot-panel"
GITHUB_URL="https://github.com/$GITHUB_REPO"

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Функция для цветного вывода
print_color() {
    echo -e "${2}${1}${NC}"
}

# Функция для логирования
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Функция для проверки успешности выполнения
check_success() {
    if [ $? -eq 0 ]; then
        print_color "✅ $1" "$GREEN"
    else
        print_color "❌ $2" "$RED"
        exit 1
    fi
}

# Проверка версии Ubuntu
check_ubuntu_version() {
    if [ ! -f /etc/os-release ]; then
        print_color "❌ Cannot determine OS version" "$RED"
        exit 1
    fi

    source /etc/os-release
    print_color "🔍 Detected OS: $PRETTY_NAME" "$BLUE"
    
    if [[ "$VERSION_ID" != "22.04" && "$VERSION_ID" != "24.04" ]]; then
        print_color "❌ This script requires Ubuntu 22.04 LTS or 24.04 LTS" "$RED"
        print_color "❌ Detected version: $VERSION_ID" "$RED"
        exit 1
    fi
    
    print_color "✅ Supported Ubuntu version: $VERSION_ID" "$GREEN"
}

# Проверка обновлений на GitHub
check_github_updates() {
    print_color "🔍 Checking for updates on GitHub..." "$BLUE"
    
    if ! command -v curl &> /dev/null; then
        apt install -y curl
    fi
    
    local latest_info
    latest_info=$(curl -s "https://api.github.com/repos/$GITHUB_REPO/releases/latest" 2>/dev/null || echo "")
    
    if [ -n "$latest_info" ] && [ "$latest_info" != "Not Found" ]; then
        local latest_version
        latest_version=$(echo "$latest_info" | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')
        
        if [ -n "$latest_version" ]; then
            print_color "📦 Latest version on GitHub: $latest_version" "$GREEN"
        else
            print_color "ℹ️  Using local version" "$BLUE"
        fi
    else
        print_color "ℹ️  Using local version" "$BLUE"
    fi
}

# Полное обновление системы
full_system_update() {
    print_color "🔄 Performing full system update..." "$BLUE"
    
    apt update
    check_success "Package list updated" "Package list update failed"
    
    apt upgrade -y
    check_success "Packages upgraded" "Package upgrade failed"
    
    apt dist-upgrade -y
    check_success "Distribution upgraded" "Distribution upgrade failed"
    
    apt autoremove -y
    apt autoclean
    check_success "System cleaned" "System cleanup failed"
    
    print_color "✅ Full system update completed" "$GREEN"
}

# Установка необходимых пакетов
install_required_packages() {
    print_color "🔄 Installing required packages..." "$BLUE"
    
    local base_packages=(
        "python3"
        "python3-pip" 
        "python3-venv"
        "git"
        "sqlite3"
        "nginx"
        "certbot"
        "python3-certbot-nginx"
        "curl"
        "wget"
        "tar"
        "gzip"
        "systemd"
        "ufw"
        "fail2ban"
        "openssl"
    )
    
    for package in "${base_packages[@]}"; do
        if ! dpkg -l | grep -q "^ii  $package "; then
            apt install -y "$package"
            print_color "✅ $package installed" "$GREEN"
        else
            print_color "✅ $package already installed" "$BLUE"
        fi
    done
    
    check_success "All required packages installed" "Package installation failed"
}

# Генерация SSL сертификата на 10 лет
generate_ssl_certificate() {
    print_color "🔐 Generating SSL certificate for 10 years..." "$BLUE"
    
    local ssl_dir="/etc/ssl/vpnbot"
    mkdir -p $ssl_dir
    
    # Генерация приватного ключа
    openssl genrsa -out $ssl_dir/private.key 4096
    
    # Создание конфигурационного файла для CSR
    cat > $ssl_dir/ssl.conf << EOF
[req]
distinguished_name = req_distinguished_name
x509_extensions = v3_req
prompt = no

[req_distinguished_name]
C = US
ST = State
L = City
O = Organization
OU = Organizational Unit
CN = vpnbot-panel

[v3_req]
keyUsage = keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = vpnbot-panel
DNS.2 = localhost
IP.1 = 127.0.0.1
EOF

    # Генерация самоподписанного сертификата на 10 лет
    openssl req -new -x509 -key $ssl_dir/private.key -out $ssl_dir/certificate.crt -days 3650 -config $ssl_dir/ssl.conf
    
    # Установка правильных прав
    chmod 600 $ssl_dir/private.key
    chmod 644 $ssl_dir/certificate.crt
    
    print_color "✅ SSL certificate generated for 10 years" "$GREEN"
}

# Настройка безопасности
setup_security() {
    print_color "🛡️  Configuring basic security..." "$BLUE"
    
    # Настройка firewall
    ufw --force reset
    echo "y" | ufw enable
    ufw allow ssh
    ufw allow http
    ufw allow https
    ufw allow 5000/tcp
    
    print_color "✅ Firewall configured" "$GREEN"
    
    # Настройка fail2ban
    if systemctl is-active --quiet fail2ban; then
        systemctl enable fail2ban
        systemctl start fail2ban
        print_color "✅ Fail2ban configured" "$GREEN"
    fi
}

# Основная установка
main_installation() {
    print_color "🚀 Starting main installation process..." "$BLUE"
    
    # Создание пользователя для бота
    if ! id "vpnbot" &>/dev/null; then
        print_color "👤 Creating vpnbot user..." "$BLUE"
        useradd -m -s /bin/bash -d /opt/vpnbot vpnbot
        check_success "vpnbot user created" "User creation failed"
    else
        print_color "✅ vpnbot user already exists" "$GREEN"
    fi

    # Создание директории для проекта
    PROJECT_DIR="/opt/vpnbot"
    print_color "📁 Setting up project directory..." "$BLUE"
    mkdir -p $PROJECT_DIR
    chown vpnbot:vpnbot $PROJECT_DIR

    # Копирование файлов проекта
    print_color "📄 Copying project files..." "$BLUE"
    
    # Создаем базовую структуру
    mkdir -p $PROJECT_DIR/templates
    
    # Копируем все Python файлы
    for file in *.py; do
        if [ -f "$file" ]; then
            cp "$file" $PROJECT_DIR/
        fi
    done
    
    # Копируем requirements.txt
    if [ -f "requirements.txt" ]; then
        cp requirements.txt $PROJECT_DIR/
    fi
    
    # Копируем шаблоны
    if [ -d "templates" ]; then
        cp templates/*.html $PROJECT_DIR/templates/ 2>/dev/null || true
    fi
    
    # Копируем version.txt
    if [ -f "version.txt" ]; then
        cp version.txt $PROJECT_DIR/
    fi
    
    chown -R vpnbot:vpnbot $PROJECT_DIR

    # Создание виртуального окружения
    print_color "🐍 Creating Python virtual environment..." "$BLUE"
    sudo -u vpnbot python3 -m venv $PROJECT_DIR/venv
    check_success "Virtual environment created" "Virtual environment creation failed"

    # Установка Python зависимостей
    print_color "📦 Installing Python dependencies..." "$BLUE"
    sudo -u vpnbot $PROJECT_DIR/venv/bin/pip install --upgrade pip
    
    if [ -f "$PROJECT_DIR/requirements.txt" ]; then
        sudo -u vpnbot $PROJECT_DIR/venv/bin/pip install -r $PROJECT_DIR/requirements.txt
    else
        # Устанавливаем зависимости вручную если файла нет
        sudo -u vpnbot $PROJECT_DIR/venv/bin/pip install python-telegram-bot yoomoney sqlalchemy requests flask flask-login gunicorn python-dotenv apscheduler
    fi
    
    check_success "Dependencies installed" "Dependency installation failed"

    # Создание конфигурационного файла
    print_color "⚙️  Creating configuration file..." "$BLUE"
    cat > $PROJECT_DIR/.env << EOF
BOT_TOKEN=YOUR_BOT_TOKEN_HERE
ADMIN_IDS=YOUR_ADMIN_ID_HERE
YOOMONEY_RECEIVER=YOUR_YOOMONEY_WALLET
YOOMONEY_TOKEN=YOUR_YOOMONEY_TOKEN
WEB_PASSWORD=$(openssl rand -base64 16)
WEB_SECRET_KEY=$(openssl rand -hex 32)
DEFAULT_LANGUAGE=ru
DATABASE_URL=sqlite:///$PROJECT_DIR/vpn_bot.db
LOG_LEVEL=INFO
LOG_FILE=$PROJECT_DIR/bot.log
WEB_HOST=0.0.0.0
WEB_PORT=5000
WEB_USERNAME=admin
CHECK_INTERVAL=300
ALERT_COOLDOWN=3600
EOF

    chown vpnbot:vpnbot $PROJECT_DIR/.env
    chmod 600 $PROJECT_DIR/.env

    # Инициализация базы данных
    print_color "🗃️ Initializing database..." "$BLUE"
    sudo -u vpnbot $PROJECT_DIR/venv/bin/python3 -c "
import sys
sys.path.append('/opt/vpnbot')
from database import init_db
init_db()
print('Database initialized successfully')
"
    check_success "Database initialized" "Database initialization failed"

    # Создание systemd службы для бота
    print_color "🔧 Creating systemd service for bot..." "$BLUE"
    cat > /etc/systemd/system/vpnbot.service << EOF
[Unit]
Description=VPN Telegram Bot
After=network.target

[Service]
Type=simple
User=vpnbot
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$PROJECT_DIR/venv/bin
ExecStart=$PROJECT_DIR/venv/bin/python3 $PROJECT_DIR/bot.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    # Создание systemd службы для веб-панели
    print_color "🔧 Creating systemd service for web panel..." "$BLUE"
    cat > /etc/systemd/system/vpnbot-web.service << EOF
[Unit]
Description=VPN Bot Web Panel
After=network.target

[Service]
Type=simple
User=vpnbot
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$PROJECT_DIR/venv/bin
ExecStart=$PROJECT_DIR/venv/bin/python3 $PROJECT_DIR/web_panel.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    # Генерация SSL сертификата
    generate_ssl_certificate

    # Настройка Nginx с SSL
    print_color "🌐 Configuring Nginx with SSL..." "$BLUE"
    cat > /etc/nginx/sites-available/vpnbot << EOF
server {
    listen 80;
    server_name _;
    return 301 https://\$host\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name _;

    ssl_certificate /etc/ssl/vpnbot/certificate.crt;
    ssl_certificate_key /etc/ssl/vpnbot/private.key;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }

    # Block access to sensitive files
    location ~ /\. {
        deny all;
    }
    
    location ~ /\.env {
        deny all;
    }
}
EOF

    ln -sf /etc/nginx/sites-available/vpnbot /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default

    # Проверка конфигурации Nginx
    nginx -t
    check_success "Nginx configuration verified" "Nginx configuration error"

    # Перезапуск Nginx
    systemctl restart nginx
    check_success "Nginx restarted" "Nginx restart failed"

    # Включение и запуск служб
    print_color "🚀 Starting services..." "$BLUE"
    systemctl daemon-reload
    systemctl enable vpnbot vpnbot-web
    systemctl start vpnbot vpnbot-web

    # Ожидание запуска служб
    sleep 5

    # Проверка статуса служб
    BOT_STATUS=$(systemctl is-active vpnbot)
    WEB_STATUS=$(systemctl is-active vpnbot-web)

    if [ "$BOT_STATUS" = "active" ] && [ "$WEB_STATUS" = "active" ]; then
        print_color "✅ Both services started successfully" "$GREEN"
    else
        print_color "⚠️  Service startup issues:" "$YELLOW"
        print_color "   Bot: $BOT_STATUS" "$YELLOW"
        print_color "   Web Panel: $WEB_STATUS" "$YELLOW"
    fi

    # Создание скриптов управления
    create_management_scripts
}

# Создание скриптов управления
create_management_scripts() {
    print_color "📜 Creating management scripts..." "$BLUE"
    
    # Основной скрипт доступа
    cat > /root/vpnbot_access.sh << 'EOF'
#!/bin/bash

print_color() {
    echo -e "${2}${1}\033[0m"
}

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'

PROJECT_DIR="/opt/vpnbot"
WEB_PASSWORD=$(grep WEB_PASSWORD $PROJECT_DIR/.env 2>/dev/null | cut -d '=' -f2)
SERVER_IP=$(curl -s -4 ifconfig.me || curl -s -6 ifconfig.me || echo "YOUR_SERVER_IP")

echo "=================================================="
print_color " VPN Bot & Web Panel Access Information" "$BLUE"
echo "=================================================="
echo ""
print_color "🌐 Web Panel URL:" "$GREEN"
print_color "   https://$SERVER_IP" "$YELLOW"
print_color "   (SSL Certificate is self-signed for 10 years)" "$YELLOW"
echo ""
print_color "🔑 Admin Credentials:" "$GREEN"
print_color "   Username: admin" "$YELLOW"
print_color "   Password: $WEB_PASSWORD" "$YELLOW"
echo ""
print_color "🤖 Telegram Bot:" "$GREEN"
print_color "   Configure via @BotFather" "$YELLOW"
print_color "   Set BOT_TOKEN in configuration" "$YELLOW"
echo ""
print_color "⚙️  Management Commands:" "$GREEN"
print_color "   systemctl status vpnbot      # Bot status" "$YELLOW"
print_color "   systemctl status vpnbot-web  # Web panel status" "$YELLOW"
print_color "   journalctl -u vpnbot -f      # Bot logs" "$YELLOW"
print_color "   journalctl -u vpnbot-web -f  # Web panel logs" "$YELLOW"
print_color "   /root/vpnbot_update.sh       # Update script" "$YELLOW"
echo ""
print_color "📊 Quick Status Check:" "$GREEN"
systemctl is-active vpnbot && print_color "   Bot: ✅ Running" "$GREEN" || print_color "   Bot: ❌ Stopped" "$RED"
systemctl is-active vpnbot-web && print_color "   Web Panel: ✅ Running" "$GREEN" || print_color "   Web Panel: ❌ Stopped" "$RED"
EOF

    chmod +x /root/vpnbot_access.sh

    # Скрипт для обновления из GitHub
    cat > /root/vpnbot_update.sh << 'EOF'
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
EOF

    chmod +x /root/vpnbot_update.sh

    # Скрипт для добавления панелей
    cat > /usr/local/bin/add_vpn_panel << 'EOF'
#!/bin/bash

if [ $# -ne 1 ]; then
    echo "Usage: add_vpn_panel 'Name;URL;Username;Password;Location'"
    echo "Example: add_vpn_panel 'Germany #1;https://panel1.com:8080;admin;pass123;Germany'"
    exit 1
fi

python3 << END
import sqlite3
from datetime import datetime

data = "$1".split(';')
if len(data) != 5:
    print("❌ Invalid format. Use: Name;URL;Username;Password;Location")
    exit(1)

name, url, username, password, location = [x.strip() for x in data]

conn = sqlite3.connect('/opt/vpnbot/vpn_bot.db')
c = conn.cursor()

c.execute('''INSERT INTO panels (name, url, username, password, location, created_at) 
             VALUES (?, ?, ?, ?, ?, ?)''',
          (name, url, username, password, location, datetime.now()))

conn.commit()
conn.close()

print("✅ Panel added successfully!")
print(f"Name: {name}")
print(f"Location: {location}")
print(f"URL: {url}")
END
EOF

    chmod +x /usr/local/bin/add_vpn_panel

    # Скрипт для мониторинга ресурсов
    cat > /usr/local/bin/panel_status << 'EOF'
#!/bin/bash

echo "🔍 Checking panel statuses..."
python3 << END
import sqlite3
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

conn = sqlite3.connect('/opt/vpnbot/vpn_bot.db')
c = conn.cursor()

c.execute("SELECT id, name, url, username, password FROM panels WHERE is_active = 1")
panels = c.fetchall()

for panel_id, name, url, username, password in panels:
    print(f"\n📊 Panel: {name}")
    print(f"🔗 URL: {url}")
    
    try:
        # Попытка получить статус панели
        auth = HTTPBasicAuth(username, password)
        response = requests.get(f"{url}/api/status", auth=auth, timeout=10, verify=False)
        
        if response.status_code == 200:
            status_data = response.json()
            print("✅ Status: Online")
            
            # Вывод информации о ресурсах если доступно
            if 'resources' in status_data:
                resources = status_data['resources']
                print(f"💾 Memory: {resources.get('memory_usage', 'N/A')}")
                print(f"💽 Disk: {resources.get('disk_usage', 'N/A')}")
                print(f"⚡ CPU: {resources.get('cpu_usage', 'N/A')}")
            
            # Получение информации о клиентах
            clients_response = requests.get(f"{url}/api/clients", auth=auth, timeout=10, verify=False)
            if clients_response.status_code == 200:
                clients = clients_response.json()
                active_clients = len([c for c in clients if c.get('enable')])
                print(f"👥 Clients: {active_clients}/{len(clients)} active")
                
        else:
            print("❌ Status: Offline")
            print(f"🔧 Response: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Status: Error - {str(e)}")

conn.close()
END
EOF

    chmod +x /usr/local/bin/panel_status
}

# Завершение установки
finish_installation() {
    print_color "🎉 Installation completed successfully!" "$GREEN"
    
    PROJECT_DIR="/opt/vpnbot"
    WEB_PASSWORD=$(grep WEB_PASSWORD $PROJECT_DIR/.env | cut -d '=' -f2)
    SERVER_IP=$(curl -s -4 ifconfig.me || curl -s -6 ifconfig.me || echo "YOUR_SERVER_IP")
    
    echo ""
    echo "=================================================="
    print_color " QUICK START GUIDE" "$BLUE"
    echo "=================================================="
    echo ""
    print_color "🌐 Web Panel Access:" "$GREEN"
    echo "   URL: https://$SERVER_IP"
    echo "   Username: admin"
    echo "   Password: $WEB_PASSWORD"
    echo "   Note: Using self-signed SSL certificate (10 years)"
    echo ""
    print_color "🤖 Telegram Bot Setup:" "$GREEN"
    echo "   1. Create bot via @BotFather"
    echo "   2. Edit: nano /opt/vpnbot/.env"
    echo "   3. Set BOT_TOKEN and ADMIN_IDS"
    echo "   4. Restart: systemctl restart vpnbot"
    echo ""
    print_color "⚙️  Management Scripts:" "$GREEN"
    echo "   /root/vpnbot_access.sh  - Access information"
    echo "   /root/vpnbot_update.sh  - Update from GitHub"
    echo "   add_vpn_panel           - Add new panel"
    echo "   panel_status            - Check panel resources"
    echo ""
    print_color "📊 Service Status:" "$GREEN"
    echo "   systemctl status vpnbot"
    echo "   systemctl status vpnbot-web"
    echo ""
    print_color "💡 Next Steps:" "$GREEN"
    echo "   1. Configure your Telegram bot"
    echo "   2. Add 3x-ui panels"
    echo "   3. Test the system"
    echo ""
    echo "=================================================="
}

# Основная функция
main() {
    # Проверка прав root
    if [ "$EUID" -ne 0 ]; then
        print_color "❌ Please run as root: sudo ./install.sh" "$RED"
        exit 1
    fi

    # Проверка версии Ubuntu
    check_ubuntu_version
    
    # Проверка обновлений на GitHub
    check_github_updates
    
    # Полное обновление системы
    full_system_update
    
    # Установка необходимых пакетов
    install_required_packages
    
    # Настройка безопасности
    setup_security
    
    # Основная установка
    main_installation
    
    # Завершение установки
    finish_installation
}

# Запуск основной функции
main "$@"
