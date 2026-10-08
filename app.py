from datetime import date

from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///expenses.db"

db = SQLAlchemy(app)


class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    expense_date = db.Column(db.Date, nullable=False, default=date.today)
    note = db.Column(db.String(200))


with app.app_context():
    db.create_all()


@app.route("/")
def home():
    return "<h1>Expense Tracker is running!</h1>"


# Temporary test routes (we will delete these in Step 3)
@app.route("/test-add")
def test_add():
    expense = Expense(title="Lunch", amount=150.0, category="Food")
    db.session.add(expense)
    db.session.commit()
    return "Sample expense saved!"


@app.route("/test-list")
def test_list():
    expenses = Expense.query.all()
    return jsonify([
        {"id": e.id, "title": e.title, "amount": e.amount,
         "category": e.category, "date": str(e.expense_date)}
        for e in expenses
    ])


if __name__ == "__main__":
    app.run(debug=True)
