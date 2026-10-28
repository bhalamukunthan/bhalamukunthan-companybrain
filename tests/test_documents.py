import fitz

from app.config import settings
from app.documents.chunker import chunk_text
from app.documents.parser import ParseError, extract_pages
import pytest


def test_chunker_keeps_paragraphs_and_splits_long_text():
    assert chunk_text("A.\n\nB.") == ["A.\n\nB."]
    long = "word " * 1000
    chunks = chunk_text(long, size=800, overlap=100)
    assert len(chunks) > 1 and all(len(c) <= 800 for c in chunks)


def test_parser_pdf_has_page_numbers():
    doc = fitz.open()
    for text in ("First page text", "Second page text"):
        doc.new_page().insert_text((72, 72), text)
    pages = extract_pages("x.pdf", doc.tobytes())
    assert [n for n, _ in pages] == [1, 2]


@pytest.mark.parametrize("name,data", [
    ("empty.txt", b""), ("blank.txt", b"   \n  "), ("fake.pdf", b"not a pdf"),
    ("bad.pdf", b"%PDF-1.4 garbage"), ("evil.exe", b"MZ..."), ("latin.txt", b"\xff\xfe\xfa"),
])
def test_parser_rejects_bad_files(name, data):
    with pytest.raises(ParseError):
        extract_pages(name, data)


def test_upload_list_download_delete(client, make_company, upload):
    _, admin = make_company()
    r = upload(admin, "Employees get 12 casual leave days.", title="Leave")
    assert r.status_code == 201
    doc_id = r.json()["id"]
    assert [d["id"] for d in client.get("/documents", headers=admin).json()] == [doc_id]
    assert client.get(f"/documents/{doc_id}/download", headers=admin).content.startswith(b"Employees")
    assert client.delete(f"/documents/{doc_id}", headers=admin).status_code == 200
    assert client.get("/documents", headers=admin).json() == []


def test_upload_validation_errors(client, make_company, upload):
    _, admin = make_company()
    assert upload(admin, "", "empty.txt").status_code == 400
    assert upload(admin, "hello world", "x.exe").status_code == 400
    assert upload(admin, "hello world", "ok.txt", roles="wizard").status_code == 400
    big = "a" * (settings.max_upload_bytes + 1)
    assert upload(admin, big, "big.txt").status_code == 413


def test_upload_requires_login(client):
    r = client.post("/documents", files={"file": ("a.txt", b"hello")})
    assert r.status_code == 401
