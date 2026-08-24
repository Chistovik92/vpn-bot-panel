"""Веб-панель VPN Bot Panel с ролевым доступом.

Безопасность: парольная авторизация, rate limit на логин,
CSRF-токены для POST-форм, защита от open redirect, аудит-лог.
"""
import logging
import secrets
import time
from functools import wraps

from flask import (
    Flask, abort, render_template, request, jsonify, session,
    redirect, url_for,
)

from app.database import Database, UserRole
from app.config import Config
from app.payment import PaymentManager

logger = logging.getLogger(__name__)

ROLE_LEVELS = {
    UserRole.USER.value: 0,
    UserRole.MODERATOR.value: 1,
    UserRole.ADMIN.value: 2,
    UserRole.SUPER_ADMIN.value: 3,
}


# --------------------------------------------------------------- rate limit
class LoginRateLimiter:
    """Простой in-memory лимитер попыток входа с блокировкой."""

    def __init__(self, max_attempts=5, lockout_seconds=1800):
        self.max_attempts = max_attempts
        self.lockout_seconds = lockout_seconds
        self._attempts = {}
        self._locked_until = {}

    def _key(self, ip, identifier):
        return f'{ip}|{identifier}'

    def is_locked(self, ip, identifier):
        until = self._locked_until.get(self._key(ip, identifier))
        if until is None:
            return False
        if time.monotonic() >= until:
            del self._locked_until[self._key(ip, identifier)]
            self._attempts.pop(self._key(ip, identifier), None)
            return False
        return True

    def record_failure(self, ip, identifier):
        key = self._key(ip, identifier)
        attempts = self._attempts.get(key, 0) + 1
        self._attempts[key] = attempts
        if attempts >= self.max_attempts:
            self._locked_until[key] = time.monotonic() + self.lockout_seconds
            logger.warning('Login locked for %s (%s failed attempts)',
                           key, attempts)

    def record_success(self, ip, identifier):
        key = self._key(ip, identifier)
        self._attempts.pop(key, None)
        self._locked_until.pop(key, None)

    def reset(self):
        self._attempts.clear()
        self._locked_until.clear()


def _safe_next(target):
    """Разрешаем только относительные пути (защита от open redirect)."""
    if target and target.startswith('/') and not target.startswith('//'):
        return target
    return None


def create_app(config=None, database=None):
    from app.config import PROJECT_ROOT
    app = Flask(
        __name__,
        template_folder=str(PROJECT_ROOT / 'templates'),
        static_folder=str(PROJECT_ROOT / 'static'),
    )
    config = config or Config()
    web_config = config.get_web_config()
    security = config.get_security_settings()

    app.secret_key = web_config['secret_key']
    app.config['DEBUG'] = web_config['debug']
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        PERMANENT_SESSION_LIFETIME=security['session_timeout_minutes'] * 60,
        MAX_CONTENT_LENGTH=1 * 1024 * 1024,
    )
    if not web_config['debug']:
        app.config['SESSION_COOKIE_SECURE'] = True

    db = database or Database()
    payment_manager = PaymentManager(db, config)
    limiter = LoginRateLimiter(
        max_attempts=security['max_login_attempts'],
        lockout_seconds=security['lockout_duration_minutes'] * 60,
    )

    # ------------------------------------------------------------ security
    @app.after_request
    def security_headers(response):
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('X-Frame-Options', 'DENY')
        response.headers.setdefault('Referrer-Policy', 'same-origin')
        return response

    @app.before_request
    def csrf_protect():
        if request.method == 'POST':
            # Внешние вебхуки аутентифицируются собственной подписью
            if request.path.startswith('/webhook/'):
                return None
            token = session.get('_csrf_token', '')
            sent = (request.form.get('_csrf_token')
                    or request.headers.get('X-CSRF-Token') or '')
            if not token or not secrets.compare_digest(token, sent):
                abort(400, description='CSRF token mismatch')

    def csrf_token():
        if '_csrf_token' not in session:
            session['_csrf_token'] = secrets.token_hex(32)
        return session['_csrf_token']

    app.jinja_env.globals['csrf_token'] = csrf_token

    # ------------------------------------------------------------- helpers
    def login_required(role=UserRole.USER.value):
        def decorator(f):
            @wraps(f)
            def decorated(*args, **kwargs):
                if 'user_id' not in session:
                    return redirect(url_for('login', next=request.path))
                needed = ROLE_LEVELS.get(role, 0)
                have = ROLE_LEVELS.get(session.get('user_role', ''), 0)
                if have < needed:
                    abort(403)
                return f(*args, **kwargs)
            return decorated
        return decorator

    @app.context_processor
    def inject_globals():
        return {'current_user_id': session.get('user_id'),
                'user_role': session.get('user_role')}

    # --------------------------------------------------------------- routes
    @app.route('/')
    @login_required(UserRole.USER.value)
    def index():
        stats = db.get_system_statistics()
        return render_template('index.html', stats=stats)

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        csrf_token()  # гарантируем наличие токена в сессии
        if request.method == 'POST':
            raw_id = (request.form.get('username') or '').strip().lstrip('@')
            password = request.form.get('password') or ''
            ip = request.remote_addr or '?'

            try:
                telegram_id = int(raw_id)
            except ValueError:
                return render_template(
                    'login.html', error='Telegram ID должен быть числом')

            if limiter.is_locked(ip, raw_id):
                logger.warning('Blocked login attempt (lockout) id=%s ip=%s',
                               raw_id, ip)
                return render_template(
                    'login.html',
                    error='Слишком много попыток. Попробуйте позже'), 429

            user = db.authenticate_user(telegram_id, password)
            if not user:
                limiter.record_failure(ip, raw_id)
                logger.warning('Failed web login for id %s from %s', raw_id, ip)
                return render_template(
                    'login.html', error='Неверный Telegram ID или пароль'), 401
            if user['is_banned']:
                return render_template('login.html', error='Аккаунт заблокирован')

            limiter.record_success(ip, raw_id)
            session.clear()
            session.permanent = True
            session['user_id'] = user['user_id']
            session['user_role'] = user['role']
            csrf_token()  # новый токен после смены сессии
            db.log_action(user['user_id'], 'web_login',
                          ip_address=request.remote_addr,
                          user_agent=request.headers.get('User-Agent'))
            dest = _safe_next(request.args.get('next')) or url_for('index')
            return redirect(dest)
        return render_template('login.html')

    @app.route('/logout', methods=['POST'])
    def logout():
        session.clear()
        return redirect(url_for('login'))

    @app.route('/admin')
    @login_required(UserRole.ADMIN.value)
    def admin_panel():
        stats = db.get_system_statistics()
        servers = db.get_servers()
        tariffs = db.get_all_tariffs()
        audit = db.get_recent_audit(limit=20)
        return render_template('admin.html', stats=stats, servers=servers,
                               tariffs=tariffs, audit=audit)

    # -------------------------------------------------------------- admin API
    @app.route('/api/toggle-user', methods=['POST'])
    @login_required(UserRole.ADMIN.value)
    def api_toggle_user():
        data = request.get_json(silent=True) or {}
        user_id = int(data.get('user_id', 0))
        if not user_id:
            return jsonify(ok=False, error='user_id required'), 400
        db.toggle_user_active(user_id)
        db.log_audit(session['user_id'], 'toggle_user',
                     f'user {user_id}', request.remote_addr)
        return jsonify(ok=True)

    @app.route('/api/toggle-server/<int:server_id>', methods=['POST'])
    @login_required(UserRole.SUPER_ADMIN.value)
    def api_toggle_server(server_id):
        db.toggle_server(server_id)
        db.log_audit(session['user_id'], 'toggle_server',
                     f'server {server_id}', request.remote_addr)
        return jsonify(ok=True)

    # ------------------------------------------------------------------ webhook
    def _verify_yoomoney_hash(form, secret):
        """Проверка sha1-подписи HTTP-уведомления YooMoney."""
        import hashlib
        parts = [
            form.get('notification_type', ''),
            form.get('operation_id', ''),
            form.get('amount', ''),
            form.get('currency', ''),
            form.get('datetime', ''),
            form.get('sender', ''),
            form.get('codepro', ''),
            form.get('label', ''),
            secret,
        ]
        digest = hashlib.sha1('&'.join(parts).encode('utf-8')).hexdigest()
        return secrets.compare_digest(digest, form.get('sha1_hash', '').lower())

    @app.route('/webhook/yoomoney', methods=['POST'])
    def webhook_yoomoney():
        pc = config.get_payment_config()
        secret = pc.get('yoomoney_notification_secret') or ''
        if not secret:
            logger.warning('YooMoney webhook received but secret not configured')
            abort(403)
        if not _verify_yoomoney_hash(request.form, secret):
            logger.warning('YooMoney webhook bad signature from %s',
                           request.remote_addr)
            abort(403)

        label = request.form.get('label', '')
        payment = db.get_payment(label) if label else None
        if not payment:
            return jsonify(ok=True, note='unknown label')

        amount = float(request.form.get('amount') or 0)
        if amount + 0.01 < payment['amount']:
            logger.warning('YooMoney webhook underpaid %s: %s < %s',
                           label, amount, payment['amount'])
            return jsonify(ok=False, note='underpaid'), 400

        result = payment_manager.activate_payment(label)
        logger.info('YooMoney webhook for %s: %s', label,
                    'activated' if result.get('success') else result.get('error'))
        return jsonify(ok=bool(result.get('success')))

    # ---------------------------------------------------------------- read API
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

    # ------------------------------------------------------------------ errors
    @app.errorhandler(400)
    def bad_request(e):  # pragma: no cover
        return 'Некорректный запрос: ' + e.description, 400

    return app


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    application = create_app()
    cfg = Config().get_web_config()
    application.run(host=cfg['host'], port=cfg['port'], debug=cfg['debug'])
