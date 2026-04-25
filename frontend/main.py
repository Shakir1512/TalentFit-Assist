import os
from typing import Any, Dict, Optional

import requests
import streamlit as st

# Configuration
API_BASE = os.getenv("BACKEND_URL", "http://localhost:8000")


# Utility functions
def token() -> Optional[str]:
    return st.session_state.get("token")


def headers() -> Dict[str, str]:
    return {"Authorization": f"Bearer {token()}"} if token() else {}


def api_request(method: str, path: str, **kwargs) -> Any:
    response = requests.request(method, f"{API_BASE}{path}", headers=headers(), timeout=30, **kwargs)
    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise RuntimeError(detail)
    return response.json()


def has_capability(name: str) -> bool:
    caps = st.session_state.get("user", {}).get("capabilities", {})
    return bool(caps.get(name))


def render_header(title: str) -> None:
    st.caption("Screening Aid - Not a Hiring Decision Tool")
    st.title(title)
    user = st.session_state.get("user")
    if user:
        st.caption(f"Signed in as {user['email']} ({user['role']})")


st.set_page_config(page_title="TalentFit Assist", page_icon="⚡", layout="wide")

# Custom CSS for professional styling
st.markdown("""
<style>
    .main { padding: 2rem 1rem; }
    .login-container { max-width: 400px; margin: 0 auto; padding: 2rem; }
    h1 { color: #1f77b4; margin-bottom: 0.5rem; }
    .header-caption { font-size: 0.9rem; color: #666; margin-bottom: 2rem; }
    .user-info { background: #f0f7ff; padding: 1rem; border-radius: 8px; margin-top: 1rem; }
</style>
""", unsafe_allow_html=True)

if not st.session_state.get("user"):
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("## ⚡ TalentFit Assist")
        st.markdown("##### Enterprise AI-Powered Screening")
        st.info("🔒 This is an AI screening aid. All hiring decisions remain with humans.")
        
        with st.form("login", clear_on_submit=False):
            st.markdown("### Sign In")
            email = st.selectbox(
                "Select Demo Account",
                [
                    "recruiter@company.com",
                    "admin@company.com",
                    "hiring-manager@company.com",
                    "auditor@company.com",
                ],
                label_visibility="collapsed"
            )
            password = st.text_input("Password", type="password", value="demo", label_visibility="collapsed")
            submitted = st.form_submit_button("🚀 Sign In", use_container_width=True)

        if submitted:
            try:
                result = api_request("POST", "/auth/login", json={"email": email, "password": password})
                st.session_state["token"] = result["token"]
                st.session_state["user"] = result["user"]
                st.rerun()
            except Exception as exc:
                st.error(f"Login failed: {exc}")
else:
    col1, col2, col3 = st.columns([1, 1, 1])
    user = st.session_state.get("user")
    with col1:
        st.markdown("### ⚡ TalentFit Assist")
    with col3:
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.clear()
            st.rerun()
    
    st.divider()
    
    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Signed in as:** {user['email']}")
        with col2:
            st.markdown(f"**Role:** `{user['role'].upper()}`")
    
    st.markdown("---")
    st.info("👋 Welcome! Use the navigation menu on the left to access screening tools.")
