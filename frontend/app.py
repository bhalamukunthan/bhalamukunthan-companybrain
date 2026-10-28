"""Streamlit interface. It is only a window: ALL security checks happen in the FastAPI backend."""
import os

import requests
import streamlit as st

API = os.getenv("API_URL", "http://127.0.0.1:8000")
ROLES = ["employee", "hr", "engineering", "admin"]
UPLOAD_ROLES = ("admin", "hr", "engineering")

st.set_page_config(page_title="CompanyBrain", page_icon="🧠", layout="centered")


def call(method, path, **kwargs):
    headers = {}
    if st.session_state.get("token"):
        headers["Authorization"] = f"Bearer {st.session_state['token']}"
    try:
        r = requests.request(method, API + path, headers=headers, timeout=180, **kwargs)
    except requests.ConnectionError:
        st.error("Cannot reach the backend. Is uvicorn running on " + API + "?")
        return None
    if r.status_code == 401 and st.session_state.get("token"):
        st.session_state.clear()
        st.error("Session expired. Please log in again.")
        st.rerun()
    if not r.ok:
        detail = r.json().get("detail", r.text) if r.headers.get("content-type", "").startswith("application/json") else r.text
        if isinstance(detail, list):
            detail = "; ".join(d.get("msg", str(d)) for d in detail)
        st.error(detail)
        return None
    return r


def start_session(token):
    st.session_state["token"] = token
    me = call("GET", "/auth/me")
    if me:
        st.session_state["me"] = me.json()
        st.session_state["messages"] = []
        st.rerun()


def login_page():
    st.title("🧠 CompanyBrain")
    st.caption("Private company knowledge assistant")
    tab_login, tab_reg = st.tabs(["Login", "Register company"])
    with tab_login:
        with st.form("login"):
            company = st.text_input("Company")
            user = st.text_input("Username")
            pw = st.text_input("Password", type="password")
            if st.form_submit_button("Log in"):
                with st.spinner("Logging in..."):
                    r = call("POST", "/auth/login", json={"company_name": company, "username": user, "password": pw})
                if r:
                    start_session(r.json()["access_token"])
    with tab_reg:
        st.write("Creates a new company and its first **admin** account. The admin adds other users later.")
        with st.form("register"):
            company = st.text_input("New company name")
            user = st.text_input("Admin username")
            pw = st.text_input("Password (min 8 characters)", type="password")
            if st.form_submit_button("Create company"):
                r = call("POST", "/auth/register-company", json={"company_name": company, "username": user, "password": pw})
                if r:
                    start_session(r.json()["access_token"])


def chat_page():
    st.header("Ask a question")
    for m in st.session_state["messages"]:
        with st.chat_message(m["role"]):
            st.write(m["text"])
            for s in m.get("sources", []):
                page = f", page {s['page']}" if s["page"] else ""
                st.caption(f"📄 {s['title']} ({s['filename']}{page})")
    q = st.chat_input("e.g. How many casual leave days do I get?")
    if q:
        st.session_state["messages"].append({"role": "user", "text": q})
        with st.spinner("Searching approved documents..."):
            r = call("POST", "/chat", json={"question": q})
        if r:
            d = r.json()
            st.session_state["messages"].append({"role": "assistant", "text": d["answer"], "sources": d["sources"]})
        st.rerun()


def upload_page():
    st.header("Upload a document")
    if st.session_state["me"]["role"] not in UPLOAD_ROLES:
        st.warning("Your role cannot upload documents.")
        return
    with st.form("upload", clear_on_submit=True):
        f = st.file_uploader("PDF or TXT (max 5 MB)", type=["pdf", "txt"])
        title = st.text_input("Title")
        dept = st.text_input("Department", value="General")
        roles = st.multiselect("Roles that may read it (admin always can)", ROLES[:-1], default=["employee"])
        if st.form_submit_button("Upload") and f:
            with st.spinner("Reading and indexing document..."):
                r = call("POST", "/documents", files={"file": (f.name, f.getvalue())},
                         data={"title": title, "department": dept, "allowed_roles": ",".join(roles)})
            if r:
                st.success(f"Uploaded: {r.json()['title']} ({r.json()['num_chunks']} chunks)")


def library_page():
    st.header("Document library")
    r = call("GET", "/documents")
    if not r:
        return
    docs = r.json()
    if not docs:
        st.info("No documents available to you yet.")
    for d in docs:
        with st.container(border=True):
            st.subheader(d["title"])
            st.caption(f"{d['filename']} · {d['department']} · roles: {', '.join(d['allowed_roles'])} · "
                       f"by {d['uploader'] or 'deleted user'} · {d['uploaded_at']}")
            if st.button("Delete", key=f"del-{d['id']}"):
                if call("DELETE", f"/documents/{d['id']}"):
                    st.rerun()


def admin_page():
    st.header("Admin")
    if st.session_state["me"]["role"] != "admin":
        st.warning("Admins only.")
        return
    st.subheader("Users")
    r = call("GET", "/admin/users")
    for u in (r.json() if r else []):
        c1, c2 = st.columns([4, 1])
        c1.write(f"**{u['username']}** — {u['role']}")
        if u["username"] != st.session_state["me"]["username"] and c2.button("Delete", key=f"u-{u['id']}"):
            if call("DELETE", f"/admin/users/{u['id']}"):
                st.rerun()
    st.subheader("Add user")
    with st.form("adduser", clear_on_submit=True):
        name = st.text_input("Username")
        pw = st.text_input("Password (min 8 characters)", type="password")
        role = st.selectbox("Role", ROLES)
        if st.form_submit_button("Create user"):
            if call("POST", "/admin/users", json={"username": name, "password": pw, "role": role}):
                st.success("User created")
                st.rerun()


if "me" not in st.session_state:
    login_page()
else:
    me = st.session_state["me"]
    st.sidebar.write(f"**{me['username']}** ({me['role']})  \n{me['company']}")
    pages = {"Chat": chat_page, "Upload": upload_page, "Library": library_page}
    if me["role"] == "admin":
        pages["Admin"] = admin_page
    choice = st.sidebar.radio("Go to", list(pages))
    if st.sidebar.button("Log out"):
        st.session_state.clear()
        st.rerun()
    pages[choice]()
