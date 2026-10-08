import csv
import os
import io
from datetime import date, datetime, timedelta

from flask import (Flask, Response, flash, redirect, render_template, request,
                   url_for)
from flask_login import (LoginManager, UserMixin, current_user, login_required,
                         login_user, logout_user)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///expenses.db")
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-later")

db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"

CATEGORIES = ["Food", "Transport", "Shopping", "Bills", "Entertainment", "Health", "Other"]


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    expenses = db.relationship("Expense", backref="owner", lazy=True,
                               cascade="all, delete-orphan")


class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
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


def get_own_expense_or_404(expense_id):
    """Return the expense only if it belongs to the logged-in user."""
    return Expense.query.filter_by(id=expense_id, user_id=current_user.id).first_or_404()


def parse_date(text):
    """Turn '2026-10-08' into a date, or None if empty or invalid."""
    try:
        return datetime.strptime(text or "", "%Y-%m-%d").date()
    except ValueError:
        return None


def filtered_expenses():
    """Build the query step by step from the URL filters. Returns (query, filters)."""
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "")
    start = parse_date(request.args.get("start"))
    end = parse_date(request.args.get("end"))

    query = Expense.query.filter_by(user_id=current_user.id)
    if q:
        query = query.filter(Expense.title.ilike(f"%{q}%"))
    if category in CATEGORIES:
        query = query.filter(Expense.category == category)
    if start:
        query = query.filter(Expense.expense_date >= start)
    if end:
        query = query.filter(Expense.expense_date <= end)

    query = query.order_by(Expense.expense_date.desc(), Expense.id.desc())
    filters = {"q": q, "category": category,
               "start": start.isoformat() if start else "",
               "end": end.isoformat() if end else ""}
    return query, filters


def csv_safe(value):
    """Stop spreadsheet formula injection (cells starting with = + - @)."""
    text = str(value or "")
    return "'" + text if text[:1] in ("=", "+", "-", "@") else text


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


# ---------- Expenses (login required, own data only) ----------

@app.route("/")
@login_required
def index():
    query, filters = filtered_expenses()
    expenses = query.all()
    total = sum(e.amount for e in expenses)
    return render_template("index.html", expenses=expenses, total=total,
                           categories=CATEGORIES, today=date.today().isoformat(),
                           filters=filters)


@app.route("/export")
@login_required
def export():
    query, _ = filtered_expenses()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Date", "Title", "Category", "Amount", "Note"])
    for e in query.all():
        writer.writerow([e.expense_date.isoformat(), csv_safe(e.title), e.category,
                         f"{e.amount:.2f}", csv_safe(e.note)])
    # "\ufeff" lets Excel read the file as UTF-8
    return Response("\ufeff" + buffer.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=expenses.csv"})


@app.route("/add", methods=["POST"])
@login_required
def add():
    data, error = read_form()
    if error:
        flash(error)
    else:
        db.session.add(Expense(user_id=current_user.id, **data))
        db.session.commit()
        flash("Expense added.")
    return redirect(url_for("index"))


@app.route("/edit/<int:expense_id>", methods=["GET", "POST"])
@login_required
def edit(expense_id):
    expense = get_own_expense_or_404(expense_id)
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
    expense = get_own_expense_or_404(expense_id)
    db.session.delete(expense)
    db.session.commit()
    flash("Expense deleted.")
    return redirect(url_for("index"))


# ---------- Dashboard ----------

@app.route("/dashboard")
@login_required
def dashboard():
    today = date.today()
    month_start = today.replace(day=1)
    next_month_start = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)

    this_month = [
        Expense.user_id == current_user.id,
        Expense.expense_date >= month_start,
        Expense.expense_date < next_month_start,
    ]

    month_total = db.session.query(func.coalesce(func.sum(Expense.amount), 0)).filter(*this_month).scalar()
    month_count = Expense.query.filter(*this_month).count()

    by_category = (db.session.query(Expense.category, func.sum(Expense.amount))
                   .filter(*this_month).group_by(Expense.category).all())

    months = []
    y, m = today.year, today.month
    for _ in range(6):
        months.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            m, y = 12, y - 1
    months.reverse()
    first_day = date.fromisoformat(months[0] + "-01")

    month_expr = func.strftime("%Y-%m", Expense.expense_date)
    rows = (db.session.query(month_expr, func.sum(Expense.amount))
            .filter(Expense.user_id == current_user.id, Expense.expense_date >= first_day)
            .group_by(month_expr).all())
    totals = dict(rows)

    return render_template(
        "dashboard.html",
        month_name=today.strftime("%B %Y"),
        month_total=month_total,
        month_count=month_count,
        category_labels=[c for c, _ in by_category],
        category_values=[round(v, 2) for _, v in by_category],
        month_labels=months,
        month_values=[round(totals.get(k, 0), 2) for k in months],
    )


if __name__ == "__main__":
    app.run(debug=True)

