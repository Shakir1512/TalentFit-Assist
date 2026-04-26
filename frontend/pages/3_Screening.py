import os
from typing import Any, Dict, Optional

import pandas as pd
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
st.title("Run Screening")

if not has_capability("can_run_screening"):
    st.error("Running screenings requires Admin or Recruiter role.")
    st.stop()

st.info("Run deterministic screening to evaluate candidate fit with job descriptions. Select from your uploaded documents.")

st.markdown("""
<style>
    .score-box { background: #d4edda; padding: 1.5rem; border-radius: 10px; margin: 1rem 0; }
    .gap-box { background: #fff3cd; padding: 1rem; border-radius: 8px; margin: 0.5rem 0; }
    .evidence-box { background: #e7f3ff; padding: 1rem; border-radius: 8px; margin: 0.5rem 0; }
</style>
""", unsafe_allow_html=True)

# Get uploaded JDs and candidates
try:
    jds_response = api_request("GET", "/uploads/jds")
    available_jds = jds_response.get("jds", {})
    jd_ids = list(available_jds.keys())
except Exception as e:
    st.error(f"Failed to fetch uploaded JDs: {e}")
    available_jds = {}
    jd_ids = []

try:
    candidates_response = api_request("GET", "/uploads/candidates")
    available_candidates = candidates_response.get("candidates", {})
    candidate_ids = list(available_candidates.keys())
except Exception as e:
    st.error(f"Failed to fetch uploaded candidates: {e}")
    available_candidates = {}
    candidate_ids = []

# Check if documents are uploaded
if not jd_ids:
    st.warning("No Job Descriptions uploaded yet. Go to Document Uploads to upload JDs first.")
    st.stop()

if not candidate_ids:
    st.warning("No Resumes uploaded yet. Go to Document Uploads to upload resumes first.")
    st.stop()

# Initialize variables
selected_jd = None
selected_candidates = []
top_k = 5
include_explanation = True
submitted = False

with st.form("screening"):
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # Select JD from uploaded list
        selected_jd = st.selectbox(
            "Select Job Description",
            jd_ids,
            format_func=lambda x: f"{x} - {available_jds[x].get('title', 'N/A')}"
        )
    
    with col2:
        # Multi-select candidates from uploaded list
        selected_candidates = st.multiselect(
            "Select Candidates to Screen",
            candidate_ids,
            format_func=lambda x: f"{x} - {available_candidates[x].get('name', 'N/A')}"
        )
    
    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        top_k = st.slider("Evidence Depth (top-K chunks)", 1, 20, 5, help="More chunks = more thorough but slower")
    with col2:
        include_explanation = st.checkbox("Generate LLM Explanation", value=True, help="Request AI-generated explanation of results")
    
    submitted = st.form_submit_button("Run Screening", use_container_width=True)

if submitted and selected_candidates:
    payload = {
        "jd_id": selected_jd,
        "candidate_ids": selected_candidates,
        "config_overrides": {"top_k": top_k},
        "generate_explanation": include_explanation,
    }
    
    with st.spinner("Running screening..."):
        try:
            result = api_request("POST", "/screen/run", json=payload)
            
            st.success("Screening Complete")
            
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Screening ID", result.get("screening_id", "N/A")[-8:])
            with col2:
                st.metric("Candidates", len(result.get("results", [])))
            with col3:
                avg_score = sum([r.get("score", 0) for r in result.get("results", [])]) / max(len(result.get("results", [])), 1)
                st.metric("Avg Score", f"{avg_score:.1%}")
            with col4:
                st.metric("Est. Cost", f"${result.get('cost_estimate', 0):.4f}")
            
            st.divider()
            
            # Results for each candidate
            st.markdown("### Candidate Results")
            
            for idx, row in enumerate(result.get("results", []), 1):
                candidate_id = row.get("candidate_id", f"Candidate {idx}")
                score = row.get("score", 0)
                
                # Score badge color based on value
                if score >= 0.75:
                    score_color = "#28a745"  # Green
                    score_label = "Strong Match"
                elif score >= 0.50:
                    score_color = "#ffc107"  # Yellow
                    score_label = "Moderate Match"
                else:
                    score_color = "#dc3545"  # Red
                    score_label = "Weak Match"
                
                with st.expander(f"**{candidate_id}** — {score_label} ({score:.1%})"):
                    # Score breakdown
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        st.markdown(f"**Overall Score:** {score:.1%}")
                        breakdown = row.get("breakdown", {})
                        if breakdown:
                            df_breakdown = pd.DataFrame([
                                {"Factor": k.replace('_', ' ').title(), "Score": f"{v:.1%}"}
                                for k, v in breakdown.items()
                            ])
                            st.dataframe(df_breakdown, use_container_width=True, hide_index=True)
                    
                    with col2:
                        compliance = row.get("policy_compliance_badge", "PASS")
                        if compliance == "PASS":
                            st.markdown("✅ Policy Compliant")
                        else:
                            st.markdown(f"⚠️ {compliance}")
                    
                    st.divider()
                    
                    # Summary explanation
                    explanation = row.get("explanation", {})
                    if explanation and include_explanation:
                        st.markdown("**Summary:**")
                        st.write(explanation.get("summary", "No summary available."))
                        
                        # Evidence cards
                        st.markdown("**Key Evidence:**")
                        evidence_cards = explanation.get("evidence_cards", [])
                        if evidence_cards:
                            for card in evidence_cards[:3]:  # Show top 3 pieces
                                st.markdown(f"- {card.get('text', 'No text')}")
            
            # Store for later reference
            st.session_state["last_screening_id"] = result.get("screening_id")
            st.markdown("---")
            st.caption(f"Screening saved with ID: {result.get('screening_id')}")
            
        except Exception as exc:
            st.error(f"Screening failed: {exc}")
