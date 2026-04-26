import os
from typing import Any, Dict, Optional, List
import io

import pandas as pd
import requests
import streamlit as st

# Try to import document parsing libraries
try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

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


def parse_csv(file) -> list:
    """Parse CSV file and return list of records"""
    df = pd.read_csv(file)
    return df.to_dict(orient='records')


def parse_txt(file) -> list:
    """Parse TXT file"""
    content = file.read().decode('utf-8')
    return [{"content": content, "id": "txt_upload"}]


def parse_pdf(file) -> list:
    """Parse PDF file and extract text"""
    if not PDF_AVAILABLE:
        st.error("PDF parsing not available. Install PyPDF2: pip install PyPDF2")
        return []
    
    try:
        pdf_reader = PyPDF2.PdfReader(file)
        text_content = ""
        
        # Extract text from all pages
        for page_num, page in enumerate(pdf_reader.pages):
            text = page.extract_text()
            text_content += f"\n--- Page {page_num + 1} ---\n{text}"
        
        if not text_content.strip():
            st.warning("No text found in PDF. Try a text-based PDF, not scanned images.")
            return []
        
        return [{"content": text_content, "id": f"pdf_{file.name}"}]
    except Exception as e:
        st.error(f"Failed to parse PDF: {e}")
        return []


def parse_docx(file) -> list:
    """Parse DOCX file and extract text"""
    if not DOCX_AVAILABLE:
        st.error("DOCX parsing not available. Install python-docx: pip install python-docx")
        return []
    
    try:
        doc = Document(file)
        text_content = ""
        
        # Extract all paragraphs
        for para in doc.paragraphs:
            if para.text.strip():
                text_content += para.text + "\n"
        
        if not text_content.strip():
            st.warning("No text found in DOCX document.")
            return []
        
        return [{"content": text_content, "id": f"docx_{file.name}"}]
    except Exception as e:
        st.error(f"Failed to parse DOCX: {e}")
        return []


def get_uploaded_jds() -> Dict[str, Any]:
    """Get list of uploaded job descriptions from backend"""
    try:
        result = api_request("GET", "/uploads/jds")
        return result.get("jds", {})
    except:
        return {}


def get_uploaded_candidates() -> Dict[str, Any]:
    """Get list of uploaded candidates from backend"""
    try:
        result = api_request("GET", "/uploads/candidates")
        return result.get("candidates", {})
    except:
        return {}


# Professional styling
st.markdown("""
<style>
    .upload-section { background: #f8f9fa; padding: 2rem; border-radius: 12px; margin-bottom: 2rem; }
    .success-box { background: #d4edda; padding: 1rem; border-radius: 8px; margin-top: 1rem; }
    .info-box { background: #e7f3ff; padding: 1rem; border-radius: 8px; margin: 1rem 0; }
    .uploaded-list { background: #f0f0f0; padding: 1rem; border-radius: 8px; margin: 1rem 0; }
</style>
""", unsafe_allow_html=True)

require_login()
st.title("Upload Documents")

if not has_capability("can_upload"):
    st.error("Uploads require Admin or Recruiter role.")
    st.stop()

st.info("Upload Job Descriptions, Resumes, and Policies. Supported formats: CSV, TXT, PDF, DOCX")

# Tabs for different upload types
tab1, tab2, tab3 = st.tabs(["Job Descriptions", "Resumes", "Policy"])

with tab1:
    st.markdown("### Upload Job Descriptions")
    st.markdown("You can upload **one file at a time** with multiple JDs inside (CSV) or single JD documents (PDF, DOCX, TXT)")
    
    jd_file = st.file_uploader(
        "Choose JD file (CSV, TXT, PDF, or DOCX)",
        type=["csv", "txt", "pdf", "docx"],
        key="jd_upload"
    )
    
    if jd_file:
        st.success(f"File selected: {jd_file.name}")
        
        try:
            if jd_file.name.endswith('.csv'):
                docs = parse_csv(jd_file)
            elif jd_file.name.endswith('.txt'):
                docs = parse_txt(jd_file)
            elif jd_file.name.endswith('.pdf'):
                docs = parse_pdf(jd_file)
            elif jd_file.name.endswith('.docx'):
                docs = parse_docx(jd_file)
            else:
                st.error("Unsupported file type")
                docs = []
            
            if docs:
                st.markdown(f"**Records found:** {len(docs)}")
                
                # Preview
                with st.expander("Preview data"):
                    st.json(docs[0] if docs else {})
                
                if st.button("Upload Job Descriptions", key="btn_upload_jd"):
                    try:
                        result = api_request("POST", "/upload/jd", json={"documents": docs})
                        st.success("Job descriptions uploaded successfully!")
                        
                        # Show uploaded JD IDs
                        st.markdown("**Uploaded JD IDs:**")
                        uploaded_ids = result.get("jd_ids", [])
                        for jd_id in uploaded_ids:
                            st.markdown(f"- `{jd_id}`")
                        
                        # Store in session for screening
                        st.session_state["uploaded_jds"] = uploaded_ids
                        
                        st.markdown(f"**Status:** {result.get('status', 'Success')}")
                        st.markdown(f"**Records processed:** {result.get('count', len(docs))}")
                    except Exception as exc:
                        st.error(f"Upload failed: {exc}")
        except Exception as exc:
            st.error(f"File parsing failed: {exc}")
    
    # Show currently uploaded JDs
    st.divider()
    st.markdown("### Currently Uploaded JDs")
    uploaded_jds = get_uploaded_jds()
    if uploaded_jds:
        for jd_id, jd_info in uploaded_jds.items():
            st.markdown(f"- **{jd_id}**: {jd_info.get('title', 'N/A')}")
    else:
        st.info("No JDs uploaded yet. Upload your first file above.")


with tab2:
    st.markdown("### Upload Resumes")
    st.markdown("You can upload **one file at a time** with multiple resumes inside (CSV) or single resumes (PDF, DOCX, TXT)")
    
    resume_file = st.file_uploader(
        "Choose resume file (CSV, TXT, PDF, or DOCX)",
        type=["csv", "txt", "pdf", "docx"],
        key="resume_upload"
    )
    
    if resume_file:
        st.success(f"File selected: {resume_file.name}")
        
        try:
            if resume_file.name.endswith('.csv'):
                docs = parse_csv(resume_file)
            elif resume_file.name.endswith('.txt'):
                docs = parse_txt(resume_file)
            elif resume_file.name.endswith('.pdf'):
                docs = parse_pdf(resume_file)
            elif resume_file.name.endswith('.docx'):
                docs = parse_docx(resume_file)
            else:
                st.error("Unsupported file type")
                docs = []
            
            if docs:
                st.markdown(f"**Records found:** {len(docs)}")
                
                # Preview
                with st.expander("Preview data"):
                    st.json(docs[0] if docs else {})
                
                if st.button("Upload Resumes", key="btn_upload_resume"):
                    try:
                        result = api_request("POST", "/upload/resume", json={"documents": docs})
                        st.success("Resumes uploaded successfully!")
                        
                        # Show uploaded candidate IDs
                        st.markdown("**Uploaded Candidate IDs:**")
                        uploaded_ids = result.get("candidate_ids", [])
                        for cand_id in uploaded_ids:
                            st.markdown(f"- `{cand_id}`")
                        
                        # Store in session for screening
                        st.session_state["uploaded_candidates"] = uploaded_ids
                        
                        st.markdown(f"**Status:** {result.get('status', 'Success')}")
                        st.markdown(f"**Records processed:** {result.get('count', len(docs))}")
                    except Exception as exc:
                        st.error(f"Upload failed: {exc}")
        except Exception as exc:
            st.error(f"File parsing failed: {exc}")
    
    # Show currently uploaded candidates
    st.divider()
    st.markdown("### Currently Uploaded Candidates")
    uploaded_candidates = get_uploaded_candidates()
    if uploaded_candidates:
        for cand_id, cand_info in uploaded_candidates.items():
            st.markdown(f"- **{cand_id}**: {cand_info.get('name', 'N/A')}")
    else:
        st.info("No resumes uploaded yet. Upload your first file above.")


with tab3:
    st.markdown("### Upload Fairness Policy")
    st.markdown("Define screening policies and fairness rules.")
    
    policy_file = st.file_uploader(
        "Choose policy file (TXT, PDF, or DOCX)",
        type=["txt", "pdf", "docx"],
        key="policy_upload"
    )
    
    if policy_file:
        st.success(f"File selected: {policy_file.name}")
        
        try:
            if policy_file.name.endswith('.txt'):
                policy_content = policy_file.read().decode('utf-8')
            elif policy_file.name.endswith('.pdf'):
                docs = parse_pdf(policy_file)
                policy_content = docs[0]['content'] if docs else ""
            elif policy_file.name.endswith('.docx'):
                docs = parse_docx(policy_file)
                policy_content = docs[0]['content'] if docs else ""
            else:
                st.error("Unsupported file type")
                policy_content = ""
            
            if policy_content:
                st.text_area("Policy Content (preview):", policy_content, height=200, disabled=True)
                
                if st.button("Upload Policy", key="btn_upload_policy"):
                    try:
                        result = api_request(
                            "POST",
                            "/upload/policy",
                            json={"policy_id": "policy_default", "content": policy_content}
                        )
                        st.success("Policy uploaded successfully!")
                        st.markdown(f"**Status:** {result.get('status', 'Success')}")
                        st.markdown(f"**Policy ID:** {result.get('policy_id', 'policy_default')}")
                    except Exception as exc:
                        st.error(f"Upload failed: {exc}")
        except Exception as exc:
            st.error(f"File parsing failed: {exc}")

st.divider()
st.markdown("""
**Supported Formats:**
- **CSV**: Multiple records with structured columns
- **PDF**: Text-based PDFs (not scanned images)
- **DOCX**: Microsoft Word documents
- **TXT**: Plain text files

All uploads are processed securely with protected attributes removed automatically.
""")

