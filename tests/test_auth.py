import sqlite3

from app.config import settings
from tests.conftest import auth


def test_register_login_me(client, make_company):
    name, admin = make_company()
    r = client.get("/auth/me", headers=admin)
    assert r.status_code == 200 and r.json()["role"] == "admin"
    r = client.post("/auth/login", json={"company_name": name, "username": "admin", "password": "Password123"})
    assert r.status_code == 200 and "access_token" in r.json()


def test_wrong_password_rejected(client, make_company):
    name, _ = make_company()
    r = client.post("/auth/login", json={"company_name": name, "username": "admin", "password": "WrongPass999"})
    assert r.status_code == 401


def test_duplicate_company_rejected(client, make_company):
    name, _ = make_company()
    r = client.post("/auth/register-company", json={"company_name": name, "username": "x1234", "password": "Password123"})
    assert r.status_code == 409


def test_weak_password_rejected(client):
    r = client.post("/auth/register-company", json={"company_name": "WeakCo", "username": "admin", "password": "short"})
    assert r.status_code == 422


def test_passwords_are_hashed_in_database(client, make_company):
    make_company()
    conn = sqlite3.connect(settings.db_path)
    hashes = [row[0] for row in conn.execute("SELECT password_hash FROM users")]
    assert hashes and all("Password123" not in h and h.startswith("$2") for h in hashes)


def test_no_token_and_fake_token_rejected(client):
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers=auth("not-a-real-token")).status_code == 401


def test_only_admin_can_manage_users(client, make_company, add_user):
    name, admin = make_company()
    emp = add_user(name, admin, "emp1", "employee")
    r = client.post("/admin/users", headers=emp, json={"username": "hacker1", "password": "Password123", "role": "admin"})
    assert r.status_code == 403
    assert client.get("/admin/users", headers=emp).status_code == 403


def test_admin_cannot_see_other_company_users(client, make_company):
    _, a1 = make_company("A")
    _, a2 = make_company("B")
    users1 = client.get("/admin/users", headers=a1).json()
    users2 = client.get("/admin/users", headers=a2).json()
    assert {u["id"] for u in users1}.isdisjoint({u["id"] for u in users2})
    other_id = users2[0]["id"]
    assert client.delete(f"/admin/users/{other_id}", headers=a1).status_code == 404
