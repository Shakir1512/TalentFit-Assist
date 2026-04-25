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
st.title("📊 Audit & Usage Dashboard")

st.markdown("""
<style>
    .metric-row { background: #f8f9fa; padding: 1.5rem; border-radius: 10px; margin-bottom: 1.5rem; }
    .alert-high { background: #f8d7da; padding: 1rem; border-radius: 8px; color: #721c24; }
    .alert-warn { background: #fff3cd; padding: 1rem; border-radius: 8px; color: #856404; }
</style>
""", unsafe_allow_html=True)

can_audit = has_capability("can_view_audit")
can_usage = has_capability("can_view_usage")

if not (can_audit or can_usage):
    st.error("❌ Audit and usage dashboards require Admin or Auditor role.")
    st.stop()

# Tabs for different dashboards
tab1, tab2 = st.tabs(["💰 Usage & Costs", "📋 Audit Logs"])

with tab1:
    st.markdown("### Token and Cost Dashboard")
    
    if can_usage:
        try:
            usage = api_request("GET", "/usage/tokens")
            
            # Key metrics
            col1, col2, col3, col4 = st.columns(4)
            
            total_tokens = usage.get("total_tokens_month", 0)
            total_cost = usage.get("total_cost_month", 0)
            budget_used_pct = usage.get("budget_used_percent", 0)
            budget_remaining = usage.get("budget_remaining", 0)
            
            with col1:
                st.metric("📌 Tokens Used", f"{total_tokens:,}")
            with col2:
                st.metric("💵 Total Cost", f"${total_cost:.4f}")
            with col3:
                st.metric("📊 Budget Used", f"{budget_used_pct}%")
            with col4:
                st.metric("✅ Budget Left", f"${budget_remaining:.2f}")
            
            # Budget warning
            if budget_used_pct > 80:
                st.markdown('<div class="alert-high">⚠️ <strong>Warning:</strong> Budget usage exceeds 80%</div>', unsafe_allow_html=True)
            elif budget_used_pct > 50:
                st.markdown('<div class="alert-warn">ℹ️ <strong>Notice:</strong> Budget usage at 50%+</div>', unsafe_allow_html=True)
            
            st.divider()
            
            # Usage records table
            st.markdown("### Usage Details")
            if usage.get("records"):
                df_usage = pd.DataFrame(usage["records"])
                
                # Format cost column
                if "cost" in df_usage.columns:
                    df_usage["cost"] = df_usage["cost"].apply(lambda x: f"${x:.4f}")
                if "tokens" in df_usage.columns:
                    df_usage["tokens"] = df_usage["tokens"].apply(lambda x: f"{int(x):,}")
                
                st.dataframe(df_usage, use_container_width=True, hide_index=True)
                st.caption(f"Total records: {len(usage.get('records', []))}")
            else:
                st.info("ℹ️ No usage records yet. Run a screening to see activity.")
                
        except Exception as exc:
            st.error(f"❌ Failed to load usage data: {exc}")
    else:
        st.warning("⚠️ You don't have permission to view usage data.")

with tab2:
    st.markdown("### Audit Logs")
    
    if can_audit:
        try:
            logs = api_request("GET", "/audit/logs")
            
            if logs.get("records"):
                # Filter options
                col1, col2, col3 = st.columns(3)
                with col1:
                    filter_action = st.selectbox(
                        "Filter by Action",
                        ["All"] + list(set([r.get("action", "unknown") for r in logs["records"]]))
                    )
                with col2:
                    filter_user = st.selectbox(
                        "Filter by User",
                        ["All"] + list(set([r.get("user_email", "unknown") for r in logs["records"]]))
                    )
                with col3:
                    filter_status = st.selectbox(
                        "Filter by Status",
                        ["All"] + list(set([r.get("status", "unknown") for r in logs["records"]]))
                    )
                
                # Apply filters
                filtered_logs = logs["records"]
                if filter_action != "All":
                    filtered_logs = [r for r in filtered_logs if r.get("action") == filter_action]
                if filter_user != "All":
                    filtered_logs = [r for r in filtered_logs if r.get("user_email") == filter_user]
                if filter_status != "All":
                    filtered_logs = [r for r in filtered_logs if r.get("status") == filter_status]
                
                st.divider()
                
                # Display logs
                st.markdown(f"### Showing {len(filtered_logs)} records")
                
                for log in filtered_logs[:50]:  # Show top 50
                    status_emoji = "✅" if log.get("status") == "success" else "❌"
                    
                    with st.expander(
                        f"{status_emoji} **{log.get('action', 'Unknown')}** — {log.get('user_email', 'Unknown')} — {log.get('timestamp', 'N/A')[:10]}"
                    ):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown(f"**User:** {log.get('user_email', 'N/A')}")
                            st.markdown(f"**Action:** {log.get('action', 'N/A')}")
                            st.markdown(f"**Status:** {log.get('status', 'N/A')}")
                        with col2:
                            st.markdown(f"**Timestamp:** {log.get('timestamp', 'N/A')}")
                            st.markdown(f"**Details:** {log.get('details', 'N/A')[:100]}...")
                
                if len(filtered_logs) > 50:
                    st.caption(f"Showing 50 of {len(filtered_logs)} records. Load older records in your system.")
            else:
                st.info("ℹ️ No audit records yet. System activity will appear here.")
                
        except Exception as exc:
            st.error(f"❌ Failed to load audit logs: {exc}")
    else:
        st.warning("⚠️ You don't have permission to view audit logs.")

st.divider()
st.markdown("**🔒 Security Note:** All data is encrypted in transit and at rest. Access logs are immutable and retained per policy.")
