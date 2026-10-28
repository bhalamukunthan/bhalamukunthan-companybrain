import os
import tempfile
import uuid

# Must be set BEFORE the app is imported. Fast fake embeddings; no model download needed.
os.environ.update(
    DATA_DIR=tempfile.mkdtemp(prefix="cb_test_"),
    EMBEDDING_BACKEND="fake",
    LLM_PROVIDER="extractive",
    SECRET_KEY="test-secret-key-test-secret-key-0123456789",
    MAX_DISTANCE="0.95",
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def make_company(client):
    """Returns a function creating a fresh company; gives (company_name, admin_headers)."""
    def _make(prefix="Co"):
        name = f"{prefix}-{uuid.uuid4().hex[:8]}"
        r = client.post("/auth/register-company", json={"company_name": name, "username": "admin", "password": "Password123"})
        assert r.status_code == 201, r.text
        return name, auth(r.json()["access_token"])
    return _make


@pytest.fixture()
def add_user(client):
    def _add(company, admin_headers, username, role):
        r = client.post("/admin/users", headers=admin_headers, json={"username": username, "password": "Password123", "role": role})
        assert r.status_code == 201, r.text
        r = client.post("/auth/login", json={"company_name": company, "username": username, "password": "Password123"})
        assert r.status_code == 200, r.text
        return auth(r.json()["access_token"])
    return _add


@pytest.fixture()
def upload(client):
    def _up(headers, text, name="doc.txt", roles="employee,hr,engineering", title="T"):
        return client.post("/documents", headers=headers, files={"file": (name, text.encode())},
                           data={"title": title, "allowed_roles": roles})
    return _up
