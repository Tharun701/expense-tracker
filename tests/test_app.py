from datetime import date

from app import User, db


def register(client, username="alice", password="secret123"):
    return client.post("/register", data={"username": username, "password": password},
                       follow_redirects=True)


def login(client, username="alice", password="secret123"):
    return client.post("/login", data={"username": username, "password": password},
                       follow_redirects=True)


def add_expense(client, title="Lunch", amount="150", category="Food"):
    return client.post("/add", data={
        "title": title, "amount": amount, "category": category,
        "expense_date": date.today().isoformat(), "note": "",
    }, follow_redirects=True)


# ---------- Authentication ----------

def test_register_and_login(client):
    register(client)
    response = login(client)
    assert b"Hi, alice" in response.data


def test_wrong_password_is_rejected(client):
    register(client)
    response = login(client, password="wrongpass")
    assert b"Wrong username or password" in response.data


def test_duplicate_username_is_rejected(client):
    register(client)
    response = register(client)
    assert b"already taken" in response.data


def test_password_is_stored_hashed(app, client):
    register(client, password="secret123")
    with app.app_context():
        user = User.query.filter_by(username="alice").first()
        assert user.password_hash != "secret123"
        assert "secret123" not in user.password_hash


def test_home_requires_login(client):
    response = client.get("/")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


# ---------- Expenses ----------

def test_add_expense_shows_in_list(client):
    register(client)
    login(client)
    response = add_expense(client, title="Biryani")
    assert b"Biryani" in response.data


def test_invalid_amount_is_rejected(client):
    register(client)
    login(client)
    response = add_expense(client, title="BadItem", amount="-5")
    assert b"greater than zero" in response.data
    assert b"BadItem" not in response.data


# ---------- Ownership (security) ----------

def test_user_cannot_edit_another_users_expense(app, client):
    register(client, "alice")
    login(client, "alice")
    add_expense(client, title="AliceSecret")

    bob = app.test_client()
    register(bob, "bob")
    login(bob, "bob")
    assert bob.get("/edit/1").status_code == 404


def test_user_cannot_delete_another_users_expense(app, client):
    register(client, "alice")
    login(client, "alice")
    add_expense(client, title="AliceSecret")

    bob = app.test_client()
    register(bob, "bob")
    login(bob, "bob")
    assert bob.post("/delete/1").status_code == 404

    # Alice's expense is still there
    assert b"AliceSecret" in client.get("/").data


# ---------- Export and dashboard ----------

def test_csv_export_blocks_formula_injection(client):
    register(client)
    login(client)
    add_expense(client, title="=1+1")
    response = client.get("/export")
    assert response.status_code == 200
    assert b"'=1+1" in response.data


def test_dashboard_loads(client):
    register(client)
    login(client)
    add_expense(client)
    assert client.get("/dashboard").status_code == 200


# ---------- CSRF ----------

def test_post_without_csrf_token_is_rejected(app):
    app.config["WTF_CSRF_ENABLED"] = True
    try:
        client = app.test_client()
        response = client.post("/register", data={"username": "mallory", "password": "secret123"})
        assert response.status_code == 400
    finally:
        app.config["WTF_CSRF_ENABLED"] = False
