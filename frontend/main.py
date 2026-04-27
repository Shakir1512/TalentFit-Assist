import os
from typing import Any, Dict, Optional

import requests
import streamlit as st

API_BASE = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="TalentFit Assist", page_icon="⚡", layout="wide")


def api_post(path: str, json_data: Dict) -> Any:
    resp = requests.post(f"{API_BASE}{path}", json=json_data, timeout=30)
    if resp.status_code >= 400:
        try:
            raise RuntimeError(resp.json().get("detail", resp.text))
        except ValueError:
            raise RuntimeError(resp.text)
    return resp.json()


def login_page() -> None:
    st.markdown("""
    <style>
        .block-container { padding-top: 4rem; }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("## ⚡ TalentFit Assist")
        st.markdown("##### Enterprise AI-Powered Screening Copilot")
        st.caption("Refracting resumes. Revealing what's really there.")
        st.divider()
        st.info("🔒 Screening aid only — all hiring decisions remain with humans.")

        with st.form("login", clear_on_submit=False):
            st.markdown("### Sign In")
            email = st.selectbox(
                "Account",
                [
                    "recruiter@company.com",
                    "admin@company.com",
                    "hiring-manager@company.com",
                    "auditor@company.com",
                ],
                label_visibility="collapsed",
            )
            password = st.text_input(
                "Password", type="password", value="demo",
                label_visibility="collapsed",
            )
            submitted = st.form_submit_button("🚀 Sign In", use_container_width=True)

        if submitted:
            try:
                result = api_post("/auth/login", {"email": email, "password": password})
                st.session_state["token"] = result["token"]
                st.session_state["user"] = result["user"]
                st.rerun()
            except Exception as exc:
                st.error(f"Login failed: {exc}")


def get_pages_for_role(role: str):
    all_pages = {
        "admin":     st.Page("pages/1_Admin_Config.py", title="Admin Config",    icon="⚙️"),
        "uploads":   st.Page("pages/2_Uploads.py",      title="Uploads",         icon="📂"),
        "screening": st.Page("pages/3_Screening.py",    title="Run Screening",   icon="🔍"),
        "review":    st.Page("pages/4_Review.py",        title="Review Results",  icon="📊"),
        "audit":     st.Page("pages/5_Audit_Usage.py",  title="Audit & Usage",   icon="📋"),
    }

    role_map = {
        "admin":          ["admin", "uploads", "screening", "review", "audit"],
        "recruiter":      ["uploads", "screening", "review"],
        "hiring_manager": ["review"],
        "auditor":        ["audit"],
    }

    keys = role_map.get(role, ["uploads", "screening", "review"])
    return [all_pages[k] for k in keys]


# ── Navigation ───────────────────────────────────────────────────────────────

if not st.session_state.get("user"):
    st.markdown("""
    <style>
        [data-testid="stSidebar"] { display: none !important; }
        [data-testid="collapsedControl"] { display: none !important; }
    </style>
    """, unsafe_allow_html=True)
    pg = st.navigation(
        [st.Page(login_page, title="Sign In", icon="🔐")],
        position="hidden",
    )
else:
    user = st.session_state["user"]
    role = user["role"]

    with st.sidebar:
        st.markdown("#### ⚡ TalentFit Assist")
        st.caption("Screening Aid — Not a Hiring Decision Tool")
        st.divider()
        st.markdown(f"**{user['email']}**")
        st.caption(f"Role: `{role.upper()}`")
        st.divider()
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    pg = st.navigation(get_pages_for_role(role))

pg.run()
