from flask import Flask

app = Flask(__name__)


@app.route("/")
def home():
    return "<h1>Expense Tracker is running!</h1>"


if __name__ == "__main__":
    app.run(debug=True)
