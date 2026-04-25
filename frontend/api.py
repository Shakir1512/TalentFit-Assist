import os
from typing import Any, Dict, Optional

import requests
import streamlit as st


API_BASE = os.getenv("BACKEND_URL", "http://localhost:8000")


def token() -> Optional[str]:
    return st.session_state.get("token")


def headers() -> Dict[str, str]:
    return {"Authorization": f"Bearer {token()}"} if token() else {}


def request(method: str, path: str, **kwargs) -> Any:
    response = requests.request(method, f"{API_BASE}{path}", headers=headers(), timeout=30, **kwargs)
    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise RuntimeError(detail)
    return response.json()


def require_login() -> None:
    if not st.session_state.get("token"):
        st.warning("Sign in to continue.")
        st.stop()


def capabilities() -> Dict[str, bool]:
    return st.session_state.get("user", {}).get("capabilities", {})


def has_capability(name: str) -> bool:
    return bool(capabilities().get(name))


def role() -> str:
    return st.session_state.get("user", {}).get("role", "anonymous")


def render_header(title: str) -> None:
    st.caption("Screening Aid - Not a Hiring Decision Tool")
    st.title(title)
    user = st.session_state.get("user")
    if user:
        st.caption(f"Signed in as {user['email']} ({user['role']})")
