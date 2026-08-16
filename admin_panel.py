#!/usr/bin/env python3
"""Flask administration panel for VPN Bot Panel."""
import os
import sys
import hashlib
import hmac
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import Database
from config import Config

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
config = Config()
db = Database()

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"))
app.secret_key = config.get_web_secret()
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")

def hash_password(password):
    salt = os.urandom(32)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return salt.hex() + ":" + digest.hex()

def verify_password(stored, provided):
    try:
        salt_hex, digest_hex = stored.split(":", 1)
        digest = hashlib.pbkdf2_hmac(
            "sha256", provided.encode("utf-8"), bytes.fromhex(salt_hex), 200_000
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False

def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get("admin_id"):
            return redirect(url_for("login", next=request.path))
        return fn(*args, **kwargs)
    return wrapped

@app.context_processor
def inject_globals():
    return {"current_admin": session.get("username")}

@app.route("/")
def index():
    return redirect(url_for("dashboard")) if session.get("admin_id") else redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("admin_id"):
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        admin = db.get_admin_by_username(username)
        if admin and verify_password(admin["password_hash"], password):
            session.clear()
            session["admin_id"] = admin["id"]
            session["username"] = admin["username"]
            session["role"] = admin["role"]
            db.update_admin_last_login(admin["id"], request.remote_addr, request.headers.get("User-Agent"))
            flash("Успешный вход.", "success")
            return redirect(request.args.get("next") or url_for("dashboard"))
        if admin:
            db.increment_login_attempts(admin["id"])
        flash("Неверное имя пользователя или пароль.", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    with db.get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM users"); total_users = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM users WHERE is_active=1"); active_users = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM payments"); total_payments = c.fetchone()[0]
        c.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE status='completed'"); revenue = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM vpn_configs WHERE is_active=1"); active_configs = c.fetchone()[0]
        c.execute("""SELECT user_id, username, full_name, registration_date FROM users
                     ORDER BY registration_date DESC LIMIT 10""")
        recent_users = [dict(x) for x in c.fetchall()]
    return render_template("dashboard.html", total_users=total_users, active_users=active_users,
                           total_payments=total_payments, total_revenue=revenue,
                           active_configs=active_configs, recent_users=recent_users)

@app.route("/users")
@login_required
def users():
    with db.get_connection() as conn:
        rows = conn.execute("""SELECT user_id, username, full_name, balance,
                               registration_date, is_active FROM users
                               ORDER BY registration_date DESC""").fetchall()
    return render_template("users.html", users=[dict(r) for r in rows])

@app.route("/users/<int:user_id>/toggle", methods=["POST"])
@login_required
def toggle_user(user_id):
    with db.get_connection() as conn:
        conn.execute("UPDATE users SET is_active=CASE is_active WHEN 1 THEN 0 ELSE 1 END WHERE user_id=?", (user_id,))
    return redirect(url_for("users"))

@app.route("/payments")
@login_required
def payments():
    with db.get_connection() as conn:
        rows = conn.execute("""SELECT p.id,p.user_id,u.username,p.amount,p.currency,
                               p.payment_date,p.payment_method,p.status,p.transaction_id
                               FROM payments p LEFT JOIN users u ON u.user_id=p.user_id
                               ORDER BY p.payment_date DESC""").fetchall()
    return render_template("payments.html", payments=[dict(r) for r in rows])

@app.route("/services")
@login_required
def services():
    with db.get_connection() as conn:
        rows = conn.execute("""SELECT id,name,description,price,duration_days,is_active
                               FROM services ORDER BY price""").fetchall()
    return render_template("services.html", services=[dict(r) for r in rows])

@app.route("/services/<int:service_id>/toggle", methods=["POST"])
@login_required
def toggle_service(service_id):
    with db.get_connection() as conn:
        conn.execute("UPDATE services SET is_active=CASE is_active WHEN 1 THEN 0 ELSE 1 END WHERE id=?", (service_id,))
    return redirect(url_for("services"))

@app.route("/settings")
@login_required
def settings():
    return render_template("settings.html", db_path=db.db_path)

@app.route("/api/statistics")
@login_required
def api_statistics():
    with db.get_connection() as conn:
        users = conn.execute("""SELECT DATE(registration_date) date,COUNT(*) count
                                FROM users WHERE registration_date>=date('now','-7 days')
                                GROUP BY DATE(registration_date) ORDER BY date""").fetchall()
        payments = conn.execute("SELECT status,COUNT(*) count FROM payments GROUP BY status").fetchall()
    return jsonify(user_stats=[dict(x) for x in users], payment_stats=[dict(x) for x in payments])

if __name__ == "__main__":
    db.init_db()
    host = os.getenv("VPN_PANEL_HOST", "127.0.0.1")
    port = int(os.getenv("VPN_PANEL_PORT", "8080"))
    app.run(host=host, port=port, debug=False)
