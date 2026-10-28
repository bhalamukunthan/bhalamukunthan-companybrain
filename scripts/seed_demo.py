"""Fills a RUNNING backend with a demo company (Acme) and a second company (Globex).
Usage: python scripts/seed_demo.py     (backend must be running on http://127.0.0.1:8000)"""
import json
from pathlib import Path

import requests

API = "http://127.0.0.1:8000"
ROOT = Path(__file__).resolve().parent.parent
PW = "DemoPass123"


def main():
    r = requests.post(f"{API}/auth/register-company", json={"company_name": "Acme", "username": "admin", "password": PW})
    if r.status_code == 409:
        print("Acme already exists. Delete the data/ folder to reseed.")
        return
    r.raise_for_status()
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    for name, role in [("hr_user", "hr"), ("eng_user", "engineering"), ("emp_user", "employee")]:
        requests.post(f"{API}/admin/users", headers=h, json={"username": name, "password": PW, "role": role}).raise_for_status()
    for item in json.loads((ROOT / "sample_data/manifest.json").read_text()):
        path = ROOT / "sample_data" / item["file"]
        with open(path, "rb") as f:
            requests.post(f"{API}/documents", headers=h, files={"file": (item["file"], f)},
                          data={"title": item["title"], "department": item["department"],
                                "allowed_roles": ",".join(item["allowed_roles"])}).raise_for_status()
    g = requests.post(f"{API}/auth/register-company", json={"company_name": "Globex", "username": "admin", "password": PW})
    g.raise_for_status()
    gh = {"Authorization": f"Bearer {g.json()['access_token']}"}
    requests.post(f"{API}/documents", headers=gh,
                  files={"file": ("globex_secret.txt", b"Globex secret: the launch date of Project Falcon is 14 March.")},
                  data={"title": "Globex Secret", "allowed_roles": "employee,hr,engineering"}).raise_for_status()
    print("Seeded. Log in as company=Acme, users: admin / hr_user / eng_user / emp_user, password:", PW)
    print("Also created company Globex (admin / same password) to demonstrate tenant isolation.")


if __name__ == "__main__":
    main()
