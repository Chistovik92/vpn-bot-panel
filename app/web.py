from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from functools import wraps
import logging
from app.database import Database, UserRole
from app.config import Config

def create_app():
    app = Flask(__name__)
    config = Config()
    web_config = config.get_web_config()
    
    app.secret_key = web_config['secret_key']
    app.config['DEBUG'] = web_config['debug']
    
    db = Database()
    
    def login_required(role=UserRole.USER.value):
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                if 'user_id' not in session:
                    return redirect(url_for('login'))
                
                user_role = db.get_user_role(session['user_id'])
                role_hierarchy = {
                    UserRole.USER.value: 0,
                    UserRole.MODERATOR.value: 1,
                    UserRole.ADMIN.value: 2,
                    UserRole.SUPER_ADMIN.value: 3
                }
                
                if role_hierarchy.get(user_role, 0) < role_hierarchy.get(role, 0):
                    return "Доступ запрещен", 403
                
                return f(*args, **kwargs)
            return decorated_function
        return decorator
    
    @app.route('/')
    @login_required(UserRole.USER.value)
    def index():
        stats = db.get_system_statistics()
        return render_template('index.html', stats=stats, user_role=session.get('user_role'))
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            telegram_id = request.form.get('telegram_id')
            # В реальной системе здесь была бы более сложная аутентификация
            user = db.get_user_by_telegram_id(int(telegram_id))
            if user:
                session['user_id'] = user['user_id']
                session['user_role'] = user['role']
                return redirect(url_for('index'))
            else:
                return render_template('login.html', error="Пользователь не найден")
        return render_template('login.html')
    
    @app.route('/logout')
    def logout():
        session.clear()
        return redirect(url_for('login'))
    
    @app.route('/admin')
    @login_required(UserRole.ADMIN.value)
    def admin_panel():
        stats = db.get_system_statistics()
        servers = db.get_servers()
        tariffs = db.get_all_tariffs()
        return render_template('admin.html', stats=stats, servers=servers, tariffs=tariffs)
    
    @app.route('/api/stats')
    @login_required(UserRole.MODERATOR.value)
    def api_stats():
        stats = db.get_system_statistics()
        return jsonify(stats)
    
    @app.route('/api/servers')
    @login_required(UserRole.ADMIN.value)
    def api_servers():
        servers = db.get_servers()
        return jsonify([dict(server) for server in servers])
    
    @app.route('/api/tariffs')
    def api_tariffs():
        tariffs = db.get_all_tariffs()
        return jsonify([dict(tariff) for tariff in tariffs])
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(
        host=app.config.get('HOST', '0.0.0.0'),
        port=app.config.get('PORT', 5000),
        debug=app.config.get('DEBUG', False)
    )