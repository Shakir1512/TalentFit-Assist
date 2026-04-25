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
st.title("📊 Review Screening Results")

if not has_capability("can_view_results"):
    st.error("❌ Review requires screening result access.")
    st.stop()

st.markdown("""
<style>
    .review-section { background: #f8f9fa; padding: 1.5rem; border-radius: 10px; margin: 1rem 0; }
    .interview-box { background: #e8f5e9; padding: 1rem; border-radius: 8px; margin: 0.5rem 0; }
    .gap-box { background: #fff3cd; padding: 1rem; border-radius: 8px; margin: 0.5rem 0; }
</style>
""", unsafe_allow_html=True)

# Load screening results
col1, col2 = st.columns([3, 1])
with col1:
    screening_id = st.text_input(
        "Screening ID",
        value=st.session_state.get("last_screening_id", ""),
        placeholder="Enter screening ID to review results"
    )
with col2:
    load_btn = st.button("🔍 Load Results", use_container_width=True)

if load_btn and screening_id:
    with st.spinner("⏳ Loading screening results..."):
        try:
            result = api_request("GET", f"/screen/results/{screening_id}")
            
            # Summary stats
            st.markdown("### 📈 Results Summary")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Candidates Reviewed", len(result.get("results", [])))
            with col2:
                scores = [r.get("score", 0) for r in result.get("results", [])]
                avg_score = sum(scores) / max(len(scores), 1)
                st.metric("Average Score", f"{avg_score:.1%}")
            with col3:
                top_score = max(scores) if scores else 0
                st.metric("Top Candidate", f"{top_score:.1%}")
            
            st.divider()
            
            # Detailed candidate reviews
            st.markdown("### 👥 Candidate Reviews")
            
            for idx, row in enumerate(result.get("results", []), 1):
                candidate_id = row.get("candidate_id", f"Candidate {idx}")
                score = row.get("score", 0)
                
                # Determine score level
                if score >= 0.75:
                    score_color = "🟢"
                    score_level = "Strong Candidate"
                elif score >= 0.50:
                    score_color = "🟡"
                    score_level = "Moderate Candidate"
                else:
                    score_color = "🔴"
                    score_level = "Weak Candidate"
                
                with st.expander(f"{score_color} **{candidate_id}** — {score_level} ({score:.1%})", expanded=idx==1):
                    # Main summary
                    st.markdown("#### Summary")
                    explanation = row.get("explanation", {})
                    st.write(explanation.get("summary", "No summary available."))
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Interview focus areas
                        st.markdown("#### 🎯 Interview Focus Areas")
                        interview_focus = explanation.get("interview_focus", [])
                        if interview_focus:
                            for i, focus in enumerate(interview_focus[:3], 1):
                                st.markdown(f"**{i}. {focus}**")
                        else:
                            st.info("No interview focus areas identified.")
                    
                    with col2:
                        # Gaps and concerns
                        st.markdown("#### ⚠️ Gaps & Concerns")
                        gaps = explanation.get("gaps", [])
                        if gaps:
                            for gap in gaps[:3]:
                                st.markdown(f"• {gap}")
                        else:
                            st.success("No significant gaps identified.")
                    
                    st.divider()
                    
                    # Evidence
                    st.markdown("#### 📋 Key Evidence")
                    evidence_cards = explanation.get("evidence_cards", [])
                    if evidence_cards:
                        for card in evidence_cards[:5]:
                            with st.container():
                                st.markdown(f"**{card.get('title', 'Evidence')}**")
                                st.caption(card.get("text", "No details"))
                    else:
                        st.info("No evidence details available.")
                    
                    # Policy compliance
                    st.markdown("#### 🛡️ Compliance")
                    compliance = row.get("policy_compliance_badge", "PASS")
                    if compliance == "PASS":
                        st.success("✅ Passes fairness policy")
                    else:
                        st.warning(f"⚠️ Policy flag: {compliance}")
            
            st.divider()
            st.caption(f"Screening ID: {screening_id}")
            
        except Exception as exc:
            st.error(f"❌ Failed to load results: {exc}")
elif load_btn:
    st.error("Please enter a Screening ID")
