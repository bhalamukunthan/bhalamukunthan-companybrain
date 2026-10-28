"""The most important tests: tenant isolation and role-based access."""
from tests.conftest import auth

SALARY = "The senior engineer salary band is 18 to 26 lakh rupees per year."
LEAVE = "Every employee receives twelve casual leave days per year."


def ask(client, headers, q):
    r = client.post("/chat", headers=headers, json={"question": q})
    assert r.status_code == 200, r.text
    return r.json()


def test_employee_cannot_upload(client, make_company, add_user, upload):
    name, admin = make_company()
    emp = add_user(name, admin, "emp1", "employee")
    assert upload(emp, "hello there friend").status_code == 403


def test_restricted_doc_hidden_from_list_download_delete_and_chat(client, make_company, add_user, upload):
    name, admin = make_company()
    hr = add_user(name, admin, "hr1", "hr")
    emp = add_user(name, admin, "emp1", "employee")
    doc_id = upload(hr, SALARY, "salary.txt", roles="hr", title="Salary Bands").json()["id"]

    # Employee: not listed, 404 on download and delete (existence not leaked)
    assert client.get("/documents", headers=emp).json() == []
    assert client.get(f"/documents/{doc_id}/download", headers=emp).status_code == 404
    assert client.delete(f"/documents/{doc_id}", headers=emp).status_code == 404

    # Employee chat: must not get the salary text or source
    res = ask(client, emp, "What is the senior engineer salary band?")
    assert res["sources"] == [] and "18 to 26" not in res["answer"]

    # HR and Admin can use it
    assert "18 to 26" in ask(client, hr, "What is the senior engineer salary band?")["answer"]
    assert "18 to 26" in ask(client, admin, "What is the senior engineer salary band?")["answer"]


def test_tenant_isolation_for_list_download_delete_and_chat(client, make_company, upload):
    _, acme = make_company("Acme")
    _, globex = make_company("Globex")
    acme_doc = upload(acme, "Project Falcon launches on 14 March at Acme.", "falcon.txt", title="Falcon").json()["id"]

    assert client.get("/documents", headers=globex).json() == []
    assert client.get(f"/documents/{acme_doc}/download", headers=globex).status_code == 404
    assert client.delete(f"/documents/{acme_doc}", headers=globex).status_code == 404
    res = ask(client, globex, "When does Project Falcon launch?")
    assert res["abstained"] is True and res["sources"] == []
    # And Acme's document is still there
    assert len(client.get("/documents", headers=acme).json()) == 1


def test_uploader_without_admin_cannot_delete_others_docs(client, make_company, add_user, upload):
    name, admin = make_company()
    hr = add_user(name, admin, "hr1", "hr")
    eng = add_user(name, admin, "eng1", "engineering")
    doc_id = upload(admin, LEAVE, "leave.txt", roles="hr,engineering").json()["id"]
    assert client.delete(f"/documents/{doc_id}", headers=hr).status_code == 403
    assert client.delete(f"/documents/{doc_id}", headers=eng).status_code == 403
    assert client.delete(f"/documents/{doc_id}", headers=admin).status_code == 200


def test_chat_abstains_when_nothing_found(client, make_company):
    _, admin = make_company()
    res = ask(client, admin, "quantum xylophone zebra nonsense")
    assert res["abstained"] is True
    assert res["answer"] == "I could not find this information in the approved documents."


def test_chat_returns_source_with_page(client, make_company, upload):
    import fitz
    _, admin = make_company()
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), "Intro page")
    doc.new_page().insert_text((72, 72), "Maternity leave is twenty six weeks")
    r = client.post("/documents", headers=admin, files={"file": ("leave.pdf", doc.tobytes())},
                    data={"title": "Leave", "allowed_roles": "employee"})
    assert r.status_code == 201
    res = ask(client, admin, "How long is maternity leave twenty six weeks")
    assert any(s["filename"] == "leave.pdf" and s["page"] == 2 for s in res["sources"])


def test_token_for_deleted_user_stops_working(client, make_company, add_user):
    name, admin = make_company()
    emp = add_user(name, admin, "temp1", "employee")
    uid = client.get("/auth/me", headers=emp).json()["id"]
    assert client.delete(f"/admin/users/{uid}", headers=admin).status_code == 200
    assert client.get("/auth/me", headers=emp).status_code == 401
