from datetime import date, datetime

from flask import Flask, flash, redirect, render_template, request, url_for
from flask_login import (LoginManager, UserMixin, current_user, login_required,
                         login_user, logout_user)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///expenses.db"
app.secret_key = "dev-secret-change-later"

db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"   # where to send people who are not logged in

CATEGORIES = ["Food", "Transport", "Shopping", "Bills", "Entertainment", "Health", "Other"]


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)


class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    expense_date = db.Column(db.Date, nullable=False, default=date.today)
    note = db.Column(db.String(200))


with app.app_context():
    db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def read_form():
    """Read and validate the form. Returns (data, error)."""
    title = request.form.get("title", "").strip()
    category = request.form.get("category", "Other")
    note = request.form.get("note", "").strip()
    try:
        amount = float(request.form.get("amount", ""))
        expense_date = datetime.strptime(request.form.get("expense_date", ""), "%Y-%m-%d").date()
    except ValueError:
        return None, "Please enter a valid amount and date."
    if not title:
        return None, "Title is required."
    if amount <= 0:
        return None, "Amount must be greater than zero."
    if category not in CATEGORIES:
        category = "Other"
    return {"title": title, "amount": amount, "category": category,
            "expense_date": expense_date, "note": note}, None


# ---------- Authentication ----------

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        if len(username) < 3:
            flash("Username must be at least 3 characters.")
        elif len(password) < 6:
            flash("Password must be at least 6 characters.")
        elif User.query.filter_by(username=username).first():
            flash("That username is already taken.")
        else:
            user = User(username=username, password_hash=generate_password_hash(password))
            db.session.add(user)
            db.session.commit()
            flash("Account created. Please log in.")
            return redirect(url_for("login"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for("index"))
        flash("Wrong username or password.")
    return render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout():
    logout_user()
    flash("You have been logged out.")
    return redirect(url_for("login"))


# ---------- Expenses (login required) ----------

@app.route("/")
@login_required
def index():
    expenses = Expense.query.order_by(Expense.expense_date.desc(), Expense.id.desc()).all()
    total = sum(e.amount for e in expenses)
    return render_template("index.html", expenses=expenses, total=total,
                           categories=CATEGORIES, today=date.today().isoformat())


@app.route("/add", methods=["POST"])
@login_required
def add():
    data, error = read_form()
    if error:
        flash(error)
    else:
        db.session.add(Expense(**data))
        db.session.commit()
        flash("Expense added.")
    return redirect(url_for("index"))


@app.route("/edit/<int:expense_id>", methods=["GET", "POST"])
@login_required
def edit(expense_id):
    expense = db.get_or_404(Expense, expense_id)
    if request.method == "POST":
        data, error = read_form()
        if error:
            flash(error)
            return redirect(url_for("edit", expense_id=expense_id))
        for key, value in data.items():
            setattr(expense, key, value)
        db.session.commit()
        flash("Expense updated.")
        return redirect(url_for("index"))
    return render_template("edit.html", expense=expense, categories=CATEGORIES)


@app.route("/delete/<int:expense_id>", methods=["POST"])
@login_required
def delete(expense_id):
    expense = db.get_or_404(Expense, expense_id)
    db.session.delete(expense)
    db.session.commit()
    flash("Expense deleted.")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
