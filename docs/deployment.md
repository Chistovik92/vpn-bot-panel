# 🚀 Развертывание VPN Bot Panel в продакшн

Полное руководство по развертыванию системы в производственной среде.

## Содержание
- [Требования к серверу](#требования-к-серверу)
- [Быстрое развертывание](#быстрое-развертывание)
- [Ручное развертывание](#ручное-развертывание)
- [Настройка обратного прокси](#настройка-обратного-прокси)
- [SSL сертификаты](#ssl-сертификаты)
- [Мониторинг и логи](#мониторинг-и-логи)
- [Резервное копирование](#резервное-копирование)
- [Обновление](#обновление)
- [Устранение неисправностей](#устранение-неисправностей)

## Требования к серверу

### Минимальные требования
- **ОС**: Ubuntu 20.04 LTS, Debian 11, CentOS 8+
- **Память**: 1 GB RAM
- **Хранилище**: 10 GB SSD
- **Процессор**: 1 ядро
- **Порты**: 80, 443, 8080 (или кастомный)

### Рекомендуемые требования
- **ОС**: Ubuntu 22.04 LTS
- **Память**: 2 GB RAM
- **Хранилище**: 20 GB SSD
- **Процессор**: 2 ядра
- **Сеть**: 100 Mbps+

### Требования к ПО
- Python 3.8+
- SQLite 3.35+
- Nginx (рекомендуется)
- Systemd

## Быстрое развертывание

### Автоматическая установка

```bash
# Скачайте скрипт установки
wget https://raw.githubusercontent.com/Chistovik92/vpn-bot-panel/main/install.sh

# Сделайте исполняемым
chmod +x install.sh

# Запустите установку
sudo ./install.sh
```
#### Скрипт установки выполнит:
* Установку системных зависимостей
* Настройку виртуального окружения Python
* Установку Python зависимостей
* Инициализацию базы данных
* Настройку супер администратора
* Настройку платежных систем
* Создание systemd сервиса
* Настройку автоматических бэкапов

## Настройка после установки

1. Настройте бота:

```bash
sudo nano /opt/vpn-bot-panel/config.ini
```
*Отредактируйте секцию [BOT]:
```ini
[BOT]
token = YOUR_ACTUAL_BOT_TOKEN
admin_telegram_id = YOUR_TELEGRAM_ID
```
2. Добавьте серверы 3x-ui:

```bash
# Через бота
/addserver

# Или через веб-панель
http://your-server:8080/admin
```
3. Проверьте работу:
```bash
sudo systemctl status vpnbot
sudo journalctl -u vpnbot -f
```
## systemd-сервисы

`/etc/systemd/system/vpnbot.service`:

```ini
[Unit]
Description=VPN Bot Panel (bot + web)
After=network.target

[Service]
Type=simple
User=vpnbot
WorkingDirectory=/opt/vpn-bot-panel
ExecStart=/opt/vpn-bot-panel/venv/bin/python run.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now vpnbot
```

После первого запуска выдайте себе пароль для веб-панели:

```bash
cd /opt/vpn-bot-panel && ./venv/bin/python -m app.manage set-password <TG_ID>
```
