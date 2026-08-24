"""Веб-панель VPN Bot Panel с ролевым доступом."""
import logging
from functools import wraps

from flask import Flask, render_template, request, jsonify, session, redirect, url_for

from app.database import Database, UserRole
from app.config import Config

logger = logging.getLogger(__name__)

ROLE_LEVELS = {
    UserRole.USER.value: 0,
    UserRole.MODERATOR.value: 1,
    UserRole.ADMIN.value: 2,
    UserRole.SUPER_ADMIN.value: 3,
}


def _safe_next(target):
    """Разрешаем только относительные пути (защита от open redirect)."""
    if target and target.startswith('/') and not target.startswith('//'):
        return target
    return None


def create_app():
    app = Flask(__name__)
    config = Config()
    web_config = config.get_web_config()

    app.secret_key = web_config['secret_key']
    app.config['DEBUG'] = web_config['debug']
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        PERMANENT_SESSION_LIFETIME=config.get_security_settings()[
            'session_timeout_minutes'] * 60,
    )

    db = Database()

    def login_required(role=UserRole.USER.value):
        def decorator(f):
            @wraps(f)
            def decorated(*args, **kwargs):
                if 'user_id' not in session:
                    return redirect(url_for('login', next=request.path))
                needed = ROLE_LEVELS.get(role, 0)
                have = ROLE_LEVELS.get(session.get('user_role', ''), 0)
                if have < needed:
                    return 'Доступ запрещен', 403
                return f(*args, **kwargs)
            return decorated
        return decorator

    @app.context_processor
    def inject_globals():
        return {'current_user_id': session.get('user_id'),
                'user_role': session.get('user_role')}

    @app.route('/')
    @login_required(UserRole.USER.value)
    def index():
        stats = db.get_system_statistics()
        return render_template('index.html', stats=stats)

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            raw_id = (request.form.get('username') or '').strip().lstrip('@')
            password = request.form.get('password') or ''
            try:
                telegram_id = int(raw_id)
            except ValueError:
                return render_template(
                    'login.html', error='Telegram ID должен быть числом')

            user = db.authenticate_user(telegram_id, password)
            if not user:
                logger.warning('Failed web login for id %s from %s',
                               raw_id, request.remote_addr)
                return render_template(
                    'login.html', error='Неверный Telegram ID или пароль')
            if user['is_banned']:
                return render_template('login.html', error='Аккаунт заблокирован')

            session.clear()
            session.permanent = True
            session['user_id'] = user['user_id']
            session['user_role'] = user['role']
            db.log_action(user['user_id'], 'web_login', ip_address=request.remote_addr)
            dest = _safe_next(request.args.get('next')) or url_for('index')
            return redirect(dest)
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
        return jsonify(db.get_system_statistics())

    @app.route('/api/servers')
    @login_required(UserRole.ADMIN.value)
    def api_servers():
        return jsonify([dict(s) for s in db.get_servers()])

    @app.route('/api/tariffs')
    @login_required(UserRole.MODERATOR.value)
    def api_tariffs():
        return jsonify([dict(t) for t in db.get_all_tariffs()])

    return app


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    application = create_app()
    cfg = Config().get_web_config()
    application.run(host=cfg['host'], port=cfg['port'], debug=cfg['debug'])
