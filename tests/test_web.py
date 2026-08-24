"""Тесты веб-панели: авторизация, CSRF, rate limit, open redirect."""
import pytest


@pytest.fixture()
def app_ctx(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / 'config.ini').write_text(
        '[DATABASE]\npath = data/web.db\n'
        '[BOT]\ntoken = T\nadmin_telegram_id = 111111\n'
        '[WEB]\nsecret_key = ' + 'x' * 32 + '\nhost = 127.0.0.1\n'
        'port = 8080\ndebug = False\n',
        encoding='utf-8')
    from app.database import Database
    from app.config import Config
    from app.web import create_app
    db = Database(str(tmp_path / 'data' / 'web.db'))
    db.set_password(111111, 'SuperSecret1')
    application = create_app(config=Config(), database=db)
    application.config['TESTING'] = True
    yield application, db


def get_csrf(client, path='/login'):
    resp = client.get(path)
    page = resp.get_data(as_text=True)
    marker = 'name="_csrf_token" value="'
    start = page.find(marker)
    assert start != -1, 'csrf token not found on page'
    start += len(marker)
    end = page.find('"', start)
    return page[start:end]


def test_safe_next_blocks_external(app_ctx):
    from app.web import _safe_next
    assert _safe_next('/dashboard') == '/dashboard'
    assert _safe_next('//evil.com') is None
    assert _safe_next('https://evil.com') is None
    assert _safe_next(None) is None


def test_login_requires_csrf(app_ctx):
    application, _ = app_ctx
    client = application.test_client()
    resp = client.post('/login', data={'username': '111111',
                                       'password': 'SuperSecret1'})
    assert resp.status_code == 400


def test_login_wrong_password(app_ctx):
    application, _ = app_ctx
    client = application.test_client()
    token = get_csrf(client)
    resp = client.post('/login', data={
        'username': '111111', 'password': 'wrong', '_csrf_token': token})
    assert resp.status_code == 401


def test_login_success_redirects_to_index(app_ctx):
    application, _ = app_ctx
    client = application.test_client()
    token = get_csrf(client)
    resp = client.post('/login', data={
        'username': '111111', 'password': 'SuperSecret1',
        '_csrf_token': token}, follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers['Location'].endswith('/')
    # Доступ к защищённой странице после входа
    index = client.get('/')
    assert index.status_code == 200


def test_open_redirect_blocked(app_ctx):
    application, _ = app_ctx
    client = application.test_client()
    token = get_csrf(client)
    resp = client.post('/login?next=//evil.com', data={
        'username': '111111', 'password': 'SuperSecret1',
        '_csrf_token': token}, follow_redirects=False)
    assert resp.status_code == 302
    assert 'evil.com' not in resp.headers['Location']


def test_rate_limit_locks(app_ctx):
    application, _ = app_ctx
    client = application.test_client()

    last_resp = None
    for _ in range(6):
        resp = client.get('/login')
        page = resp.get_data(as_text=True)
        marker = 'name="_csrf_token" value="'
        start = page.find(marker) + len(marker)
        token = page[start:page.find('"', start)]
        last_resp = client.post('/login', data={
            'username': '999999', 'password': 'bad', '_csrf_token': token})
    assert last_resp.status_code in (401, 429)

    # После блокировки даже правильный пароль отклоняется с 429
    resp = client.get('/login')
    page = resp.get_data(as_text=True)
    marker = 'name="_csrf_token" value="'
    start = page.find(marker) + len(marker)
    token = page[start:page.find('"', start)]
    locked = client.post('/login', data={
        'username': '999999', 'password': 'anything', '_csrf_token': token})
    assert locked.status_code == 429


def test_admin_route_requires_role(app_ctx):
    application, db = app_ctx
    db.create_user(222222, 'plain', 'Plain User')
    db.set_password(222222, 'UserPass1')

    client = application.test_client()
    token = get_csrf(client)
    client.post('/login', data={
        'username': '222222', 'password': 'UserPass1', '_csrf_token': token})

    assert client.get('/').status_code == 200          # обычная страница ок
    assert client.get('/admin').status_code == 403     # в админку нельзя
