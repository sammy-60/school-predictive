# app.py
import os
import click
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import (
    LoginManager, login_user, login_required, logout_user, current_user
)
from flask_migrate import Migrate

# local imports
from models import db, User

# ------------------------------------------------------------------------------
# App & Config
# ------------------------------------------------------------------------------
app = Flask(__name__, template_folder="templates", static_folder="static")

# Change this in production or set SECRET_KEY in environment
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-change-me")

# DB: use env DATABASE_URL if present, else SQLite (easy for dev)
# Example MySQL: mysql+mysqldb://root:password@localhost/school_db?charset=utf8mb4
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///school.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Init extensions
db.init_app(app)
migrate = Migrate(app, db)

login_manager = LoginManager(app)
login_manager.login_view = "login"    # redirect here if not logged in
login_manager.login_message_category = "info"


@login_manager.user_loader
def load_user(user_id: str):
    return User.query.get(int(user_id))


# ------------------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------------------
@app.route("/")
def home():
    return redirect(url_for("dashboard" if current_user.is_authenticated else "login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    message = None
    if request.method == "POST":
        email_or_username = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        # allow either email or username in the "email" field
        user = (
            User.query.filter_by(email=email_or_username).first()
            or User.query.filter_by(username=email_or_username).first()
        )

        if user and user.check_password(password):
            login_user(user)
            flash(f"Welcome, {user.username}!", "success")
            return redirect(url_for("dashboard"))
        else:
            message = "Invalid email/username or password"

    return render_template("login.html", message=message, title="SMS-PRA")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    # You can branch UI by role here
    # if current_user.role == "student": ...
    # if current_user.role == "faculty": ...
    # if current_user.role == "admin": ...
    return render_template("dashboard.html", title="Dashboard", user=current_user)


# ------------------------------------------------------------------------------
# CLI helper to create users (safe & easy)
# ------------------------------------------------------------------------------
@app.cli.command("create-user")
@click.option("--username", prompt=True)
@click.option("--email", prompt=True)
@click.option("--role", type=click.Choice(["student", "faculty", "admin"]), prompt=True)
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
def create_user(username, email, role, password):
    """Create a user from the command line."""
    with app.app_context():
        if User.query.filter((User.username == username) | (User.email == email)).first():
            click.echo("A user with that username or email already exists.")
            return
        u = User(username=username, email=email, role=role)
        u.set_password(password)
        db.session.add(u)
        db.session.commit()
        click.echo(f"✅ Created user {username} ({role})")


# ------------------------------------------------------------------------------
# Entrypoint (optional when you use `flask run`)
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    # running directly: `python app.py`
    with app.app_context():
        # ensure DB file exists on first run when using SQLite
        db.create_all()
    app.run(debug=True)
