# Expense Tracker

A full stack web app to record, search and analyse personal expenses.

**Live demo:** https://expense-tracker-jmsj.onrender.com (free tier, may take about a minute to wake up)

## Features
- User registration and login with hashed passwords
- Add, edit and delete expenses
- Each user can only access their own data
- Search by title, filter by category and date range
- Dashboard with monthly total, category pie chart and 6-month bar chart
- Export filtered expenses to CSV

## Tech stack
- Python, Flask, Flask-Login, Flask-SQLAlchemy
- SQLite
- HTML, Jinja templates, Bootstrap 5, Chart.js
- Gunicorn, deployed on Render

## Security notes
- Passwords hashed with Werkzeug
- Ownership checks on every edit and delete, which prevents access to other users' records
- Parameterized queries through SQLAlchemy
- CSV export sanitizes cells that could run as spreadsheet formulas
- Secrets stored in environment variables

## Run locally
1. git clone https://github.com/Tharun701/expense-tracker.git
2. cd expense-tracker
3. python -m venv venv
4. venv\Scripts\Activate.ps1
5. pip install -r requirements.txt
6. python app.py
7. Open http://127.0.0.1:5000

## Future improvements
- PostgreSQL and database migrations
- CSRF protection with Flask-WTF
- Automated tests with pytest
- Monthly budgets and alerts


