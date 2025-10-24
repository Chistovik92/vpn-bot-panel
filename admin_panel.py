#!/usr/bin/env python3
"""
VPN Bot Panel - Админ панель управления
Web-интерфейс для управления VPN ботом
"""

import os
import sys
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from functools import wraps
import hashlib
import json

# Добавляем текущую директорию в путь для импорта
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from database import Database
    from config import Config
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    sys.exit(1)

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SESSION_TYPE'] = 'filesystem'

# Загрузка конфигурации
config = Config()
db = Database()

def hash_password(password):
    """Хеширование пароля"""
    import hashlib
    salt = os.urandom(32)
    password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
    return salt.hex() + ':' + password_hash.hex()

def verify_password(stored_password, provided_password):
    """Проверка пароля"""
    try:
        salt_hex, password_hash_hex = stored_password.split(':')
        salt = bytes.fromhex(salt_hex)
        new_hash = hashlib.pbkdf2_hmac('sha256', provided_password.encode(), salt, 100000)
        return new_hash.hex() == password_hash_hex
    except:
        return False

def login_required(f):
    """Декоратор для проверки авторизации"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
@login_required
def index():
    """Главная страница админ-панели"""
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Страница входа"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        try:
            admin = db.get_admin_by_username(username)
            if admin and verify_password(admin['password_hash'], password):
                session['admin_id'] = admin['id']
                session['username'] = admin['username']
                session['role'] = admin['role']
                
                # Обновляем время последнего входа
                db.update_admin_last_login(admin['id'], 
                                         request.remote_addr,
                                         request.headers.get('User-Agent'))
                
                flash('✅ Успешный вход в систему!', 'success')
                return redirect(url_for('index'))
            else:
                flash('❌ Неверное имя пользователя или пароль', 'error')
        except Exception as e:
            flash(f'❌ Ошибка при входе: {str(e)}', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Выход из системы"""
    session.clear()
    flash('✅ Вы вышли из системы', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Панель управления"""
    try:
        # Статистика пользователей
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Общее количество пользователей
            cursor.execute('SELECT COUNT(*) FROM users')
            total_users = cursor.fetchone()[0]
            
            # Активные пользователи
            cursor.execute('SELECT COUNT(*) FROM users WHERE is_active = 1')
            active_users = cursor.fetchone()[0]
            
            # Общее количество платежей
            cursor.execute('SELECT COUNT(*) FROM payments')
            total_payments = cursor.fetchone()[0]
            
            # Сумма всех платежей
            cursor.execute('SELECT SUM(amount) FROM payments WHERE status = "completed"')
            total_revenue = cursor.fetchone()[0] or 0
            
            # Последние пользователи
            cursor.execute('''
                SELECT user_id, username, full_name, registration_date 
                FROM users 
                ORDER BY registration_date DESC 
                LIMIT 5
            ''')
            recent_users = cursor.fetchall()
            
            # Последние платежи
            cursor.execute('''
                SELECT p.user_id, u.username, p.amount, p.payment_date, p.status
                FROM payments p
                LEFT JOIN users u ON p.user_id = u.user_id
                ORDER BY p.payment_date DESC 
                LIMIT 5
            ''')
            recent_payments = cursor.fetchall()
            
        return render_template('dashboard.html',
                             total_users=total_users,
                             active_users=active_users,
                             total_payments=total_payments,
                             total_revenue=total_revenue,
                             recent_users=recent_users,
                             recent_payments=recent_payments)
                             
    except Exception as e:
        flash(f'❌ Ошибка загрузки статистики: {str(e)}', 'error')
        return render_template('dashboard.html')

@app.route('/users')
@login_required
def users():
    """Управление пользователями"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT user_id, username, full_name, balance, registration_date, is_active
                FROM users 
                ORDER BY registration_date DESC
            ''')
            users_list = cursor.fetchall()
            
        return render_template('users.html', users=users_list)
    except Exception as e:
        flash(f'❌ Ошибка загрузки пользователей: {str(e)}', 'error')
        return render_template('users.html', users=[])

@app.route('/payments')
@login_required
def payments():
    """Управление платежами"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT p.id, p.user_id, u.username, p.amount, p.payment_date, 
                       p.payment_method, p.status, p.transaction_id
                FROM payments p
                LEFT JOIN users u ON p.user_id = u.user_id
                ORDER BY p.payment_date DESC
            ''')
            payments_list = cursor.fetchall()
            
        return render_template('payments.html', payments=payments_list)
    except Exception as e:
        flash(f'❌ Ошибка загрузки платежей: {str(e)}', 'error')
        return render_template('payments.html', payments=[])

@app.route('/services')
@login_required
def services():
    """Управление услугами"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, name, description, price, duration_days, is_active
                FROM services 
                ORDER BY price ASC
            ''')
            services_list = cursor.fetchall()
            
        return render_template('services.html', services=services_list)
    except Exception as e:
        flash(f'❌ Ошибка загрузки услуг: {str(e)}', 'error')
        return render_template('services.html', services=[])

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """Настройки системы"""
    if request.method == 'POST':
        try:
            # Здесь будет обработка изменения настроек
            flash('✅ Настройки успешно сохранены', 'success')
        except Exception as e:
            flash(f'❌ Ошибка сохранения настроек: {str(e)}', 'error')
    
    return render_template('settings.html')

@app.route('/api/statistics')
@login_required
def api_statistics():
    """API для получения статистики"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Статистика по дням (последние 7 дней)
            cursor.execute('''
                SELECT DATE(registration_date) as date, COUNT(*) as count
                FROM users 
                WHERE registration_date >= date('now', '-7 days')
                GROUP BY DATE(registration_date)
                ORDER BY date
            ''')
            user_stats = cursor.fetchall()
            
            # Статистика платежей
            cursor.execute('''
                SELECT status, COUNT(*) as count 
                FROM payments 
                GROUP BY status
            ''')
            payment_stats = cursor.fetchall()
            
        return jsonify({
            'user_stats': [{'date': row[0], 'count': row[1]} for row in user_stats],
            'payment_stats': [{'status': row[0], 'count': row[1]} for row in payment_stats]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Шаблоны HTML
@app.route('/templates/<template_name>')
def serve_template(template_name):
    """Сервис для отдачи HTML шаблонов"""
    templates = {
        'index.html': '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VPN Bot Panel - Главная</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Arial, sans-serif; background: #f5f5f5; }
        .header { background: #2c3e50; color: white; padding: 1rem; }
        .nav { display: flex; justify-content: space-between; align-items: center; }
        .nav-links a { color: white; text-decoration: none; margin-left: 1rem; }
        .container { max-width: 1200px; margin: 2rem auto; padding: 0 1rem; }
        .welcome { background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .welcome h1 { color: #2c3e50; margin-bottom: 1rem; }
        .quick-stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem; margin-top: 2rem; }
        .stat-card { background: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .stat-card h3 { color: #7f8c8d; margin-bottom: 0.5rem; }
        .stat-number { font-size: 2rem; font-weight: bold; color: #2c3e50; }
    </style>
</head>
<body>
    <div class="header">
        <div class="nav">
            <h1>VPN Bot Panel</h1>
            <div class="nav-links">
                <a href="/dashboard">Панель управления</a>
                <a href="/users">Пользователи</a>
                <a href="/payments">Платежи</a>
                <a href="/settings">Настройки</a>
                <a href="/logout">Выйти</a>
            </div>
        </div>
    </div>
    
    <div class="container">
        <div class="welcome">
            <h1>Добро пожаловать в панель управления VPN Bot!</h1>
            <p>Используйте меню выше для навигации по разделам панели управления.</p>
            
            <div class="quick-stats">
                <div class="stat-card">
                    <h3>Общее руководство</h3>
                    <p>Для полного управления системой используйте терминальное меню:</p>
                    <code style="background: #f8f9fa; padding: 0.5rem; display: block; margin-top: 1rem;">
                        sudo ./Boot-main-ini
                    </code>
                </div>
                <div class="stat-card">
                    <h3>Быстрый доступ</h3>
                    <ul style="margin-top: 1rem;">
                        <li><a href="/dashboard">📊 Статистика</a></li>
                        <li><a href="/users">👥 Пользователи</a></li>
                        <li><a href="/payments">💳 Платежи</a></li>
                        <li><a href="/settings">⚙️ Настройки</a></li>
                    </ul>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
        ''',
        
        'login.html': '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VPN Bot Panel - Вход</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Arial, sans-serif; background: #2c3e50; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
        .login-container { background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); width: 100%; max-width: 400px; }
        .login-header { text-align: center; margin-bottom: 2rem; }
        .login-header h1 { color: #2c3e50; margin-bottom: 0.5rem; }
        .form-group { margin-bottom: 1rem; }
        label { display: block; margin-bottom: 0.5rem; color: #555; }
        input[type="text"], input[type="password"] { width: 100%; padding: 0.75rem; border: 1px solid #ddd; border-radius: 4px; font-size: 1rem; }
        button { width: 100%; padding: 0.75rem; background: #3498db; color: white; border: none; border-radius: 4px; font-size: 1rem; cursor: pointer; }
        button:hover { background: #2980b9; }
        .flash-messages { margin-bottom: 1rem; }
        .flash-message { padding: 0.75rem; border-radius: 4px; margin-bottom: 0.5rem; }
        .flash-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .flash-error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .flash-info { background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="login-header">
            <h1>VPN Bot Panel</h1>
            <p>Вход в систему управления</p>
        </div>
        
        <div class="flash-messages">
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                        <div class="flash-message flash-{{ category }}">{{ message }}</div>
                    {% endfor %}
                {% endif %}
            {% endwith %}
        </div>
        
        <form method="POST" action="/login">
            <div class="form-group">
                <label for="username">Имя пользователя:</label>
                <input type="text" id="username" name="username" required>
            </div>
            
            <div class="form-group">
                <label for="password">Пароль:</label>
                <input type="password" id="password" name="password" required>
            </div>
            
            <button type="submit">Войти</button>
        </form>
        
        <div style="margin-top: 1rem; text-align: center; color: #666;">
            <p>Используйте учетные данные, созданные при установке</p>
        </div>
    </div>
</body>
</html>
        ''',
        
        'dashboard.html': '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VPN Bot Panel - Панель управления</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Arial, sans-serif; background: #f5f5f5; }
        .header { background: #2c3e50; color: white; padding: 1rem; }
        .nav { display: flex; justify-content: space-between; align-items: center; }
        .nav-links a { color: white; text-decoration: none; margin-left: 1rem; }
        .container { max-width: 1200px; margin: 2rem auto; padding: 0 1rem; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1.5rem; margin-bottom: 2rem; }
        .stat-card { background: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; }
        .stat-card h3 { color: #7f8c8d; margin-bottom: 0.5rem; font-size: 0.9rem; }
        .stat-number { font-size: 2rem; font-weight: bold; color: #2c3e50; }
        .recent-activity { background: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .recent-activity h2 { color: #2c3e50; margin-bottom: 1rem; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 0.75rem; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #f8f9fa; font-weight: bold; }
        .flash-messages { margin-bottom: 1rem; }
        .flash-message { padding: 0.75rem; border-radius: 4px; margin-bottom: 0.5rem; }
        .flash-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .flash-error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
    </style>
</head>
<body>
    <div class="header">
        <div class="nav">
            <h1>VPN Bot Panel</h1>
            <div class="nav-links">
                <a href="/">Главная</a>
                <a href="/dashboard">Панель управления</a>
                <a href="/users">Пользователи</a>
                <a href="/payments">Платежи</a>
                <a href="/settings">Настройки</a>
                <a href="/logout">Выйти</a>
            </div>
        </div>
    </div>
    
    <div class="container">
        <div class="flash-messages">
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                        <div class="flash-message flash-{{ category }}">{{ message }}</div>
                    {% endfor %}
                {% endif %}
            {% endwith %}
        </div>
        
        <h1 style="color: #2c3e50; margin-bottom: 1.5rem;">Панель управления</h1>
        
        <div class="stats-grid">
            <div class="stat-card">
                <h3>Всего пользователей</h3>
                <div class="stat-number">{{ total_users }}</div>
            </div>
            <div class="stat-card">
                <h3>Активных пользователей</h3>
                <div class="stat-number">{{ active_users }}</div>
            </div>
            <div class="stat-card">
                <h3>Всего платежей</h3>
                <div class="stat-number">{{ total_payments }}</div>
            </div>
            <div class="stat-card">
                <h3>Общий доход</h3>
                <div class="stat-number">{{ "%.2f"|format(total_revenue) }} ₽</div>
            </div>
        </div>
        
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem;">
            <div class="recent-activity">
                <h2>Последние пользователи</h2>
                {% if recent_users %}
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Имя пользователя</th>
                            <th>Дата регистрации</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for user in recent_users %}
                        <tr>
                            <td>{{ user[0] }}</td>
                            <td>{{ user[1] or 'N/A' }}</td>
                            <td>{{ user[3] }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
                {% else %}
                <p>Нет данных о пользователях</p>
                {% endif %}
            </div>
            
            <div class="recent-activity">
                <h2>Последние платежи</h2>
                {% if recent_payments %}
                <table>
                    <thead>
                        <tr>
                            <th>Пользователь</th>
                            <th>Сумма</th>
                            <th>Статус</th>
                            <th>Дата</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for payment in recent_payments %}
                        <tr>
                            <td>{{ payment[1] or payment[0] }}</td>
                            <td>{{ "%.2f"|format(payment[2]) }} ₽</td>
                            <td>{{ payment[4] }}</td>
                            <td>{{ payment[3] }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
                {% else %}
                <p>Нет данных о платежах</p>
                {% endif %}
            </div>
        </div>
    </div>
</body>
</html>
        '''
    }
    
    if template_name in templates:
        return templates[template_name]
    else:
        return "Template not found", 404

if __name__ == '__main__':
    # Загрузка конфигурации панели
    panel_config = {}
    if os.path.exists('panel_config.json'):
        with open('panel_config.json', 'r') as f:
            panel_config = json.load(f)
    
    port = panel_config.get('admin_panel_port', 5000)
    host = panel_config.get('admin_panel_host', '0.0.0.0')
    debug = panel_config.get('debug', False)
    
    print(f"🚀 Запуск админ-панели на http://{host}:{port}")
    print(f"📊 Доступ к панели: http://localhost:{port}")
    print("⏹️  Для остановки нажмите Ctrl+C")
    
    app.run(host=host, port=port, debug=debug)