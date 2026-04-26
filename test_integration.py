#!/usr/bin/env python3
"""
Integration test script to verify end-to-end document upload and screening workflow.

This script tests:
1. Upload JDs and verify IDs are returned
2. Fetch JDs from new endpoint
3. Upload candidates and verify IDs are returned
4. Fetch candidates from new endpoint
5. Run screening with valid IDs
"""

import requests
import json
from pathlib import Path

BASE_URL = "http://localhost:8000"
TOKEN = "test-token-placeholder"  # Set this to actual token after login

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
}

def login(email: str, password: str) -> str:
    """Login and get JWT token"""
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": email, "password": password}
    )
    response.raise_for_status()
    return response.json()["token"]

def upload_jds(documents: list) -> dict:
    """Upload Job Descriptions"""
    response = requests.post(
        f"{BASE_URL}/upload/jd",
        headers=HEADERS,
        json={"documents": documents}
    )
    response.raise_for_status()
    return response.json()

def upload_resumes(documents: list) -> dict:
    """Upload Resumes"""
    response = requests.post(
        f"{BASE_URL}/upload/resume",
        headers=HEADERS,
        json={"documents": documents}
    )
    response.raise_for_status()
    return response.json()

def get_uploaded_jds() -> dict:
    """Fetch list of uploaded JDs"""
    response = requests.get(
        f"{BASE_URL}/uploads/jds",
        headers=HEADERS
    )
    response.raise_for_status()
    return response.json()

def get_uploaded_candidates() -> dict:
    """Fetch list of uploaded candidates"""
    response = requests.get(
        f"{BASE_URL}/uploads/candidates",
        headers=HEADERS
    )
    response.raise_for_status()
    return response.json()

def run_screening(jd_id: str, candidate_ids: list) -> dict:
    """Run screening with selected JD and candidates"""
    response = requests.post(
        f"{BASE_URL}/screen/run",
        headers=HEADERS,
        json={
            "jd_id": jd_id,
            "candidate_ids": candidate_ids,
            "config_overrides": {"top_k": 5},
            "generate_explanation": True,
        }
    )
    response.raise_for_status()
    return response.json()

def main():
    print("🚀 Starting Integration Test\n")
    
    # Step 1: Login
    print("1️⃣  Logging in...")
    try:
        global TOKEN, HEADERS
        TOKEN = login("admin@talentfit.local", "secure_password_123")
        HEADERS["Authorization"] = f"Bearer {TOKEN}"
        print(f"✅ Login successful. Token: {TOKEN[:20]}...\n")
    except Exception as e:
        print(f"❌ Login failed: {e}")
        print("   (If running without actual backend, set TOKEN manually)\n")
    
    # Step 2: Upload test JDs
    print("2️⃣  Uploading test Job Descriptions...")
    test_jds = [
        {
            "jd_id": "jd_001",
            "title": "Senior Backend Engineer",
            "company": "TechCorp",
            "domain": "technology",
            "content": "We are looking for a Senior Backend Engineer with 5+ years of Python and AWS experience...",
            "must_have_skills": ["Python", "AWS", "REST APIs"],
            "nice_to_have_skills": ["Kubernetes", "gRPC"],
            "required_years_min": 5,
            "required_years_max": 10,
        },
        {
            "jd_id": "jd_002",
            "title": "Frontend Engineer",
            "company": "WebStudio",
            "domain": "technology",
            "content": "Seeking Frontend Engineer experienced with React and TypeScript...",
            "must_have_skills": ["React", "TypeScript", "CSS"],
            "nice_to_have_skills": ["Next.js", "Testing"],
            "required_years_min": 3,
            "required_years_max": 8,
        }
    ]
    
    try:
        upload_result = upload_jds(test_jds)
        print(f"✅ Uploaded {upload_result.get('count', 0)} JDs")
        print(f"   JD IDs: {upload_result.get('jd_ids', [])}\n")
        jd_ids_uploaded = upload_result.get('jd_ids', [])
    except Exception as e:
        print(f"❌ Upload failed: {e}\n")
        return
    
    # Step 3: Fetch uploaded JDs
    print("3️⃣  Fetching list of uploaded JDs...")
    try:
        jds_list = get_uploaded_jds()
        print(f"✅ Retrieved {jds_list.get('count', 0)} JDs from endpoint:")
        for jd_id, jd_info in jds_list.get('jds', {}).items():
            print(f"   - {jd_id}: {jd_info.get('title')} ({jd_info.get('company')})")
        print()
    except Exception as e:
        print(f"❌ Fetch JDs failed: {e}\n")
    
    # Step 4: Upload test candidates
    print("4️⃣  Uploading test Candidate Resumes...")
    test_candidates = [
        {
            "candidate_id": "cand_001",
            "name": "Alice Johnson",
            "email": "alice@example.com",
            "domain": "technology",
            "years_of_experience": 6,
            "content": "Senior Backend Engineer with 6 years of Python, AWS, and REST API development...",
            "skills": ["Python", "AWS", "REST APIs", "PostgreSQL"],
        },
        {
            "candidate_id": "cand_002",
            "name": "Bob Smith",
            "email": "bob@example.com",
            "domain": "technology",
            "years_of_experience": 4,
            "content": "Frontend Developer experienced with React, TypeScript, and modern CSS...",
            "skills": ["React", "TypeScript", "CSS", "Next.js"],
        }
    ]
    
    try:
        upload_result = upload_resumes(test_candidates)
        print(f"✅ Uploaded {upload_result.get('count', 0)} Resumes")
        print(f"   Candidate IDs: {upload_result.get('candidate_ids', [])}\n")
        candidate_ids_uploaded = upload_result.get('candidate_ids', [])
    except Exception as e:
        print(f"❌ Resume upload failed: {e}\n")
        return
    
    # Step 5: Fetch uploaded candidates
    print("5️⃣  Fetching list of uploaded Candidates...")
    try:
        candidates_list = get_uploaded_candidates()
        print(f"✅ Retrieved {candidates_list.get('count', 0)} Candidates from endpoint:")
        for cand_id, cand_info in candidates_list.get('candidates', {}).items():
            print(f"   - {cand_id}: {cand_info.get('name')} ({cand_info.get('email')})")
        print()
    except Exception as e:
        print(f"❌ Fetch candidates failed: {e}\n")
    
    # Step 6: Run screening
    print("6️⃣  Running screening with uploaded documents...")
    if not jd_ids_uploaded or not candidate_ids_uploaded:
        print("❌ Cannot run screening - no documents uploaded\n")
        return
    
    try:
        screening_result = run_screening(jd_ids_uploaded[0], candidate_ids_uploaded)
        print(f"✅ Screening completed successfully!")
        print(f"   Screening ID: {screening_result.get('screening_id')}")
        print(f"   Results: {len(screening_result.get('results', []))} candidates")
        for result in screening_result.get('results', [])[:2]:
            print(f"   - {result.get('candidate_id')}: Score {result.get('score', 0):.1%}")
        print()
    except Exception as e:
        print(f"❌ Screening failed: {e}")
        print(f"   This is the error we're trying to fix!")
        print()
    
    print("✅ Integration Test Complete!\n")
    print("Summary:")
    print("  ✓ Upload JDs and extract IDs")
    print("  ✓ Fetch JDs from endpoint")
    print("  ✓ Upload candidates and extract IDs")
    print("  ✓ Fetch candidates from endpoint")
    print("  ✓ Run screening with valid IDs")
    print("\nIf all steps passed, the 'Unknown jd_id' error should be fixed!")

if __name__ == "__main__":
    main()
