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


def require_login() -> None:
    if not st.session_state.get("token"):
        st.warning("Sign in to continue.")
        st.stop()


def has_capability(name: str) -> bool:
    caps = st.session_state.get("user", {}).get("capabilities", {})
    return bool(caps.get(name))


def render_header(title: str) -> None:
    st.caption("Screening Aid - Not a Hiring Decision Tool")
    st.title(title)
    user = st.session_state.get("user")
    if user:
        st.caption(f"Signed in as {user['email']} ({user['role']})")


require_login()
st.title("⚙️ System Configuration")

if not has_capability("can_edit_config"):
    st.error("❌ Configuration requires Admin role.")
    st.stop()

st.markdown("""
<style>
    .config-section { background: #f8f9fa; padding: 1.5rem; border-radius: 10px; margin-bottom: 1.5rem; }
    .metric-box { background: #e8f4f8; padding: 1rem; border-radius: 8px; display: inline-block; margin: 0.5rem; }
</style>
""", unsafe_allow_html=True)

try:
    current = api_request("GET", "/config")["config"]
except Exception as exc:
    st.error(f"Failed to load configuration: {exc}")
    st.stop()

st.info("⚙️ Adjust system parameters for AI screening. Changes take effect immediately.")

# Display current settings in a metrics row
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Temperature", f"{current.get('temperature', 0.7):.1f}")
with col2:
    st.metric("Max Tokens", current.get("max_tokens", 1500))
with col3:
    st.metric("Top-K Retrieval", current.get("top_k", 5))
with col4:
    st.metric("Budget Used", f"${current.get('used_tokens_cost', 0):.2f}")

st.divider()

with st.form("config"):
    # Model Configuration
    with st.expander("🤖 Model Settings", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            llm_model = st.selectbox(
                "LLM Model",
                ["claude-haiku-4-5", "claude-sonnet-4-5", "claude-opus-4-5"],
                index=0
            )
            embedding_model = st.selectbox(
                "Embedding Model",
                ["text-embedding-3-small", "text-embedding-3-large", "all-MiniLM-L6-v2"],
                index=0
            )
        with col2:
            temperature = st.slider(
                "Temperature (creativity)",
                0.0, 2.0,
                float(current.get("temperature", 0.7)),
                0.1
            )
            max_tokens = st.number_input(
                "Max Tokens",
                64, 4000,
                int(current.get("max_tokens", 1500)),
                50
            )

    # Retrieval Settings
    with st.expander("🔍 Retrieval & Chunking"):
        col1, col2, col3 = st.columns(3)
        with col1:
            top_k = st.slider(
                "Top-K Results",
                1, 50,
                int(current.get("top_k", 5))
            )
        with col2:
            chunk_size = st.number_input(
                "Chunk Size",
                128, 4000,
                int(current.get("chunking", {}).get("resume", {}).get("chunk_size", 512)),
                50
            )
        with col3:
            chunk_overlap = st.number_input(
                "Chunk Overlap",
                0, 1000,
                int(current.get("chunking", {}).get("resume", {}).get("overlap", 50)),
                10
            )

    # Scoring Weights
    with st.expander("📊 Scoring Weights"):
        st.markdown("Configure how each factor contributes to the final score:")
        weights = current.get("scoring_weights", {})
        col1, col2, col3 = st.columns(3)
        with col1:
            must = st.slider("Must-have Skills", 0.0, 1.0, float(weights.get("must_have", 0.4)), 0.05)
            nice = st.slider("Nice-to-have Skills", 0.0, 1.0, float(weights.get("nice_to_have", 0.2)), 0.05)
        with col2:
            exp = st.slider("Experience Match", 0.0, 1.0, float(weights.get("experience", 0.2)), 0.05)
            domain = st.slider("Domain Relevance", 0.0, 1.0, float(weights.get("domain", 0.1)), 0.05)
        with col3:
            ambiguity = st.slider("Ambiguity Penalty", 0.0, 1.0, float(weights.get("ambiguity", 0.1)), 0.05)
        
        # Show total
        total = must + nice + exp + domain + ambiguity
        st.markdown(f"**Total Weight:** {total:.2f} (should be close to 1.0)")

    # Budget & Guardrails
    with st.expander("🛡️ Safety & Budget"):
        col1, col2 = st.columns(2)
        with col1:
            guardrail = st.selectbox(
                "Guardrail Level",
                ["HIGH", "MEDIUM", "LOW"],
                index=0,
                help="HIGH: Strict checks, MEDIUM: Balanced, LOW: Permissive"
            )
        with col2:
            budget = st.number_input(
                "Monthly Token Budget ($)",
                1, 100_000_000,
                int(current.get("monthly_token_budget", 500)),
                1000
            )

    st.divider()
    submitted = st.form_submit_button("💾 Save Configuration", use_container_width=True)

if submitted:
    payload = {
        "llm_model": llm_model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "embedding_model": embedding_model,
        "top_k": top_k,
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
        "scoring_weights": {
            "must_have": must,
            "nice_to_have": nice,
            "experience": exp,
            "domain": domain,
            "ambiguity": ambiguity,
        },
        "guardrail_strictness": guardrail,
        "monthly_token_budget": budget,
    }
    try:
        result = api_request("POST", "/config/update", json=payload)
        st.success("✅ Configuration saved successfully!")
        st.rerun()
    except Exception as exc:
        st.error(f"Failed to save configuration: {exc}")
