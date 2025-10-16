from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import sqlite3
from datetime import datetime, timedelta
import json
import logging
import subprocess
import requests
from requests.auth import HTTPBasicAuth
import os
import sys

# Добавляем путь к проекту для импорта модулей
sys.path.append('/opt/vpnbot')

from database import SessionLocal, Panel, Subscription, User, Payment, Alert
import config
from languages import get_web_text

app = Flask(__name__)
app.secret_key = config.WEB_SECRET_KEY
app.config['TEMPLATES_AUTO_RELOAD'] = True

# Настройка логирования
logging.basicConfig(level=config.LOG_LEVEL)
logger = logging.getLogger(__name__)

class WebUser(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

@login_manager.user_loader
def load_user(user_id):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if user and user.user_id in config.ADMIN_IDS:
            return WebUser(user.id, user.username)
        return None
    finally:
        db.close()

def get_language():
    """Получить текущий язык из сессии или браузера"""
    if 'language' in session:
        return session['language']
    
    browser_lang = request.accept_languages.best_match(['ru', 'en'])
    session['language'] = browser_lang or config.DEFAULT_LANGUAGE
    return session['language']

@app.context_processor
def inject_language():
    """Добавить функции языка в контекст шаблонов"""
    language = get_language()
    return dict(
        _=lambda key: get_web_text(language, key),
        current_language=language
    )

@app.route('/')
def index():
    """Главная страница - редирект на дашборд для авторизованных, иначе на логин"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Страница входа"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    language = get_language()
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == config.WEB_USERNAME and password == config.WEB_PASSWORD:
            db = SessionLocal()
            try:
                admin_user = db.query(User).filter(User.user_id.in_(config.ADMIN_IDS)).first()
                if admin_user:
                    user = WebUser(admin_user.id, admin_user.username)
                    login_user(user)
                    logger.info(f"Web user {username} logged in successfully")
                    return redirect(url_for('dashboard'))
                else:
                    flash('Administrator not found in database', 'error')
            finally:
                db.close()
        else:
            flash(get_web_text(language, 'invalid_credentials'), 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Выход из системы"""
    logout_user()
    flash('You have been logged out successfully', 'success')
    return redirect(url_for('login'))

@app.route('/set_language/<lang>')
def set_language(lang):
    """Смена языка"""
    if lang in ['ru', 'en']:
        session['language'] = lang
    return redirect(request.referrer or url_for('dashboard'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Дашборд администратора"""
    db = SessionLocal()
    try:
        language = get_language()
        
        # Общая статистика
        total_users = db.query(User).count()
        total_active_subs = db.query(Subscription).filter(Subscription.is_active == True).count()
        total_panels = db.query(Panel).count()
        
        # Доходы
        total_revenue = db.query(Payment).filter(Payment.status == 'completed').with_entities(
            db.func.sum(Payment.amount)
        ).scalar() or 0
        
        # Активные панели
        active_panels = db.query(Panel).filter(
            Panel.is_active == True,
            Panel.last_check > datetime.utcnow() - timedelta(minutes=10)
        ).count()
        
        # Последние платежи
        recent_payments = db.query(Payment).filter(Payment.status == 'completed').order_by(
            Payment.completed_at.desc()
        ).limit(10).all()
        
        # Последние алерты
        recent_alerts = db.query(Alert).filter(Alert.is_resolved == False).order_by(
            Alert.created_at.desc()
        ).limit(10).all()
        
        # Статистика по панелям
        panels_stats = []
        panels = db.query(Panel).all()
        for panel in panels:
            clients_count = db.query(Subscription).filter(
                Subscription.panel_id == panel.id, 
                Subscription.is_active == True
            ).count()
            
            status = "online" if panel.last_check and panel.last_check > datetime.utcnow() - timedelta(minutes=10) else "offline"
            
            panels_stats.append({
                'id': panel.id,
                'name': panel.name,
                'location': panel.location,
                'status': status,
                'clients_count': clients_count,
                'max_clients': panel.max_clients,
                'url': panel.url
            })
        
        return render_template('dashboard.html',
                            total_users=total_users,
                            total_active_subs=total_active_subs,
                            total_panels=total_panels,
                            active_panels=active_panels,
                            total_revenue=total_revenue,
                            recent_payments=recent_payments,
                            recent_alerts=recent_alerts,
                            panels_stats=panels_stats)
    
    finally:
        db.close()

@app.route('/panels')
@login_required
def panels():
    """Управление панелями"""
    db = SessionLocal()
    try:
        panels_list = db.query(Panel).order_by(Panel.created_at.desc()).all()
        return render_template('panels.html', panels=panels_list)
    finally:
        db.close()

@app.route('/panel/<int:panel_id>')
@login_required
def panel_detail(panel_id):
    """Детальная информация о панели"""
    db = SessionLocal()
    try:
        panel = db.query(Panel).filter(Panel.id == panel_id).first()
        if not panel:
            flash('Panel not found', 'error')
            return redirect(url_for('panels'))
        
        # Получение информации о ресурсах панели
        panel_resources = get_panel_resources(panel)
        
        # Подключения на этой панели
        subscriptions = db.query(Subscription).filter(
            Subscription.panel_id == panel_id
        ).order_by(Subscription.created_at.desc()).all()
        
        return render_template('panel_detail.html', 
                             panel=panel, 
                             subscriptions=subscriptions,
                             resources=panel_resources)
    finally:
        db.close()

@app.route('/subscriptions')
@login_required
def subscriptions():
    """Управление подписками"""
    db = SessionLocal()
    try:
        status_filter = request.args.get('status', 'all')
        
        query = db.query(Subscription)
        if status_filter == 'active':
            query = query.filter(Subscription.is_active == True)
        elif status_filter == 'inactive':
            query = query.filter(Subscription.is_active == False)
        
        subscriptions_list = query.order_by(Subscription.created_at.desc()).all()
        return render_template('subscriptions.html', 
                             subscriptions=subscriptions_list,
                             status_filter=status_filter)
    finally:
        db.close()

@app.route('/users')
@login_required
def users():
    """Управление пользователями"""
    db = SessionLocal()
    try:
        users_list = db.query(User).order_by(User.created_at.desc()).all()
        return render_template('users.html', users=users_list)
    finally:
        db.close()

@app.route('/payments')
@login_required
def payments():
    """Управление платежами"""
    db = SessionLocal()
    try:
        status_filter = request.args.get('status', 'all')
        
        query = db.query(Payment)
        if status_filter != 'all':
            query = query.filter(Payment.status == status_filter)
        
        payments_list = query.order_by(Payment.created_at.desc()).all()
        return render_template('payments.html', 
                             payments=payments_list,
                             status_filter=status_filter)
