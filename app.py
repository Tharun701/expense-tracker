from datetime import date, datetime

from flask import Flask, flash, redirect, render_template, request, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///expenses.db"
app.secret_key = "dev-secret-change-later"

db = SQLAlchemy(app)

CATEGORIES = ["Food", "Transport", "Shopping", "Bills", "Entertainment", "Health", "Other"]


class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    expense_date = db.Column(db.Date, nullable=False, default=date.today)
    note = db.Column(db.String(200))


with app.app_context():
    db.create_all()


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


@app.route("/")
def index():
    expenses = Expense.query.order_by(Expense.expense_date.desc(), Expense.id.desc()).all()
    total = sum(e.amount for e in expenses)
    return render_template("index.html", expenses=expenses, total=total,
                           categories=CATEGORIES, today=date.today().isoformat())


@app.route("/add", methods=["POST"])
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
def delete(expense_id):
    expense = db.get_or_404(Expense, expense_id)
    db.session.delete(expense)
    db.session.commit()
    flash("Expense deleted.")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
