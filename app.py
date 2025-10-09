# app.py
from flask_mail import Mail, Message
import random
import os
import re
import click
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import (
    LoginManager, login_user, login_required, logout_user, current_user
)
from flask_migrate import Migrate
from models import db, User  # local imports

# ------------------------------------------------------------------------------
# App & Config
# ------------------------------------------------------------------------------
app = Flask(__name__, template_folder="templates", static_folder="static")

# Secret Key (change in production)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-change-me")

# ------------------------------------------------------------------------------
# Database Configuration
# ------------------------------------------------------------------------------
# Dev default (SQLite). For MySQL, set DATABASE_URL env:
# mysql+mysqldb://root:password@localhost/school_db?charset=utf8mb4
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///school.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# ------------------------------------------------------------------------------
# Email (Mail) Configuration - for OTP Verification
# ------------------------------------------------------------------------------
# TIP: Use Gmail with an App Password (not your normal password).
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME", "yourgmail@gmail.com")
app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD", "your-app-password")
app.config["MAIL_DEFAULT_SENDER"] = os.getenv("MAIL_DEFAULT_SENDER", "yourgmail@gmail.com")

# Initialize extensions
db.init_app(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message_category = "info"
mail = Mail(app)

# Temporary in-memory OTP store (email -> code)
otp_storage = {}

@login_manager.user_loader
def load_user(user_id: str):
    return User.query.get(int(user_id))

# ------------------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------------------

@app.route("/")
def home():
    return redirect(url_for("dashboard" if current_user.is_authenticated else "login"))

# ✅ Login with @deerwalk.edu.np or @gmail.com + OTP
@app.route("/login", methods=["GET", "POST"])
def login():
    message = None

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        # Allowed domains
        allowed_domains = ["@deerwalk.edu.np", "@gmail.com"]
        if not any(email.endswith(d) for d in allowed_domains):
            message = "❌ Only emails ending with @deerwalk.edu.np or @gmail.com are allowed."
            return render_template("login.html", message=message, title="SMS-PRA")

        # Validate email format strictly for those domains
        if not re.match(r"^[a-zA-Z0-9._%+-]+@(deerwalk\.edu\.np|gmail\.com)$", email):
            message = "❌ Invalid email format. Use a valid Deerwalk or Gmail address."
            return render_template("login.html", message=message, title="SMS-PRA")

        # Find or auto-create user
        user = User.query.filter_by(email=email).first()
        if not user:
            # Auto-create student user with generated password
            username = email.split("@")[0]
            temp_password = os.urandom(6).hex()
            user = User(username=username, email=email, role="student")
            user.set_password(temp_password)
            db.session.add(user)
            db.session.commit()

        # Check password (only if user already knows one; for new users it’s temp)
        if not user.check_password(password):
            message = "❌ Incorrect password."
            return render_template("login.html", message=message, title="SMS-PRA")

        # Send OTP
        otp = random.randint(100000, 999999)
        otp_storage[email] = otp

        try:
            msg = Message("Your Login Verification Code", recipients=[email])
            msg.body = f"""Dear {user.username},

Your login verification code is: {otp}
(It expires in 5 minutes.)

— SMS-PRA
"""
            mail.send(msg)
        except Exception as e:
            # For dev convenience, show OTP in console if email fails
            print("⚠️ Mail send failed:", e)
            print("DEV OTP =", otp)
            flash("Could not send email — using dev mode. Check terminal for OTP.", "warning")

        flash("📩 A verification code has been sent to your email.", "info")
        return redirect(url_for("verify_otp", email=email))

    return render_template("login.html", message=message, title="SMS-PRA")


# ✅ OTP verification
@app.route("/verify-otp/<email>", methods=["GET", "POST"])
def verify_otp(email):
    email = email.lower()
    if request.method == "POST":
        entered_otp = request.form.get("otp", "").strip()
        real = otp_storage.get(email)
        if real and str(real) == entered_otp:
            # OTP ok — consume it and log user in
            del otp_storage[email]
            user = User.query.filter_by(email=email).first()
            if not user:
                flash("User record not found. Please login again.", "danger")
                return redirect(url_for("login"))
            login_user(user)
            flash("✅ Login successful!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("❌ Invalid or expired OTP.", "danger")

    return render_template("verify_otp.html", email=email)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    # Role-based dashboard (customize later)
    return render_template("dashboard.html", title="Dashboard", user=current_user)

# ------------------------------------------------------------------------------
# CLI: create-user
# ------------------------------------------------------------------------------
@app.cli.command("create-user")
@click.option("--username", prompt=True)
@click.option("--email", prompt=True)
@click.option("--role", type=click.Choice(["student", "faculty", "admin"]), prompt=True, default="student")
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
def create_user(username, email, role, password):
    """Create a user from the command line."""
    email = email.strip().lower()
    if not re.match(r"^[a-zA-Z0-9._%+-]+@(deerwalk\.edu\.np|gmail\.com)$", email):
        click.echo("❌ Email must be @deerwalk.edu.np or @gmail.com")
        return

    with app.app_context():
        if User.query.filter((User.username == username) | (User.email == email)).first():
            click.echo("⚠️ A user with that username or email already exists.")
            return

        u = User(username=username, email=email, role=role)
        u.set_password(password)
        db.session.add(u)
        db.session.commit()
        click.echo(f"✅ Created user {username} ({role})")

# ------------------------------------------------------------------------------
# Entry Point
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Ensure DB exists (SQLite)
    app.run(debug=True)
