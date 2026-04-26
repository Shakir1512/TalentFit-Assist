# Quick Test Guide: Verify the Bug Fix

## TL;DR - The Fix in 30 Seconds

**Problem:** Upload docs, then screening says "Unknown jd_id: jd_001" ❌  
**Solution:** Backend now tracks IDs and frontend uses dropdowns ✅  

**Test It:**
1. Upload CSV with JDs → Backend returns jd_ids
2. Go to Screening → Dropdown shows uploaded JDs
3. Select JD + candidates → Click "Run Screening"
4. ✅ Works! (no more "Unknown jd_id" error)

---

## Detailed Test Scenarios

### Test 1: CSV Upload → Verify IDs Returned

**What to do:**
1. Open 2_Uploads.py page
2. Select "Job Descriptions" tab
3. Upload `test_data/sample_jds.csv`
4. Click "Upload"

**What to expect:**
- ✅ Success message shows "Successfully uploaded 5 Job Descriptions"
- ✅ IDs displayed: jd_001, jd_002, jd_003, jd_004, jd_005
- ✅ Titles shown: "Senior Backend Engineer", "Frontend Engineer", etc.

**Why this matters:** Backend is returning the IDs it created

---

### Test 2: Screening Dropdown Shows Uploaded JDs

**What to do:**
1. (After uploading above) Navigate to 3_Screening.py page
2. Look at the "Select Job Description" dropdown

**What to expect:**
- ✅ Dropdown (not text input!) shows 5 options
- ✅ Options display: "jd_001 - Senior Backend Engineer"
- ✅ Each option shows ID and title from backend

**Why this matters:** Frontend fetched real uploaded documents

---

### Test 3: Resume Upload → Verify Candidate IDs

**What to do:**
1. Navigate to 2_Uploads.py page  
2. Select "Resumes" tab
3. Upload `test_data/sample_resumes.csv`
4. Click "Upload"

**What to expect:**
- ✅ Success message shows "Successfully uploaded 10 Resumes"
- ✅ Candidate IDs displayed: cand_001, cand_002, ..., cand_010
- ✅ Names shown: "Alice Johnson", "Bob Smith", etc.

**Why this matters:** Resume upload also returns candidate IDs

---

### Test 4: Screening Shows Uploaded Candidates

**What to do:**
1. (After uploading resumes) Refresh 3_Screening.py page
2. Look at "Select Candidates to Screen" multiselect

**What to expect:**
- ✅ Multiselect (not text area!) shows 10 options
- ✅ Options display: "cand_001 - Alice Johnson"  
- ✅ Can select multiple candidates

**Why this matters:** Frontend lists real uploaded candidates

---

### Test 5: Run Screening with Selected Documents (THE KEY TEST!)

**What to do:**
1. Go to 3_Screening.py
2. Select a JD from dropdown (e.g., "jd_001")
3. Select 2-3 candidates from multiselect
4. Click "Run Screening"

**What to expect:**
```
✅ SUCCESS - Results appear with:
   - Screening ID
   - Average score across candidates
   - Individual results for each candidate
   - Score breakdown (skills, experience, etc.)
   - Evidence cards
```

**NOT expecting:**
```
❌ "Screening failed: 'Unknown jd_id: jd_001'"
❌ "Unknown candidate_id: cand_001"
❌ Any ID-related errors
```

**Why this matters:** THIS IS THE BUG FIX! IDs are now guaranteed valid.

---

### Test 6: Mixed Format Upload (CSV + PDF + DOCX)

**What to do:**
1. Go to 2_Uploads.py → "Job Descriptions" tab
2. Upload different formats:
   - One PDF: `test_data/jd_jd_001.pdf`
   - One DOCX: create by combining JD records
   - One TXT: create manual test file

**What to expect:**
- ✅ All three formats accepted and parsed
- ✅ All get assigned IDs
- ✅ All appear in 3_Screening.py dropdown

**Why this matters:** System supports multi-format workflow

---

### Test 7: Error Handling - No Documents

**What to do:**
1. Clear browser cache/session state
2. Navigate directly to 3_Screening.py WITHOUT uploading
3. Look for warnings

**What to expect:**
```
⚠️ "No Job Descriptions uploaded yet. Go to Document Uploads to upload JDs first."
⚠️ "No Resumes uploaded yet. Go to Document Uploads to upload resumes first."
```

**Why this matters:** Graceful error handling prevents confusion

---

### Test 8: Error Handling - Empty Upload

**What to do:**
1. Create empty CSV file
2. Try to upload via 2_Uploads.py

**What to expect:**
```
❌ Error message explaining format/content issue
```

**Why this matters:** Invalid data doesn't crash system

---

## API-Level Testing (Advanced)

### Endpoint 1: GET /uploads/jds
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:8000/uploads/jds

# Expected response:
{
  "status": "success",
  "count": 5,
  "jds": {
    "jd_001": {
      "title": "Senior Backend Engineer",
      "company": "TechCorp",
      "domain": "technology",
      "uploaded_at": "2024-12-19T10:30:00"
    },
    ...
  }
}
```

### Endpoint 2: GET /uploads/candidates
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:8000/uploads/candidates

# Expected response:
{
  "status": "success",
  "count": 10,
  "candidates": {
    "cand_001": {
      "name": "Alice Johnson",
      "email": "alice@example.com",
      "years_of_experience": 6,
      "domain": "technology",
      "uploaded_at": "2024-12-19T10:35:00"
    },
    ...
  }
}
```

### Endpoint 3: POST /upload/jd (Response Check)
```bash
curl -X POST -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"documents": [{"jd_id": "test_001", "title": "Test", "content": "..."}]}' \
     http://localhost:8000/upload/jd

# Expected response includes:
{
  "status": "success",
  "count": 1,
  "jd_ids": ["test_001"],        # NEW FIELD!
  "uploaded": 1,
  "processed": {...}
}
```

---

## Pass/Fail Checklist

### Critical Path (Must Pass)
- [ ] Upload CSV JDs → Get jd_ids back
- [ ] GET /uploads/jds returns all JDs
- [ ] Screening page shows JD dropdown
- [ ] Upload CSV resumes → Get candidate_ids back
- [ ] GET /uploads/candidates returns all candidates  
- [ ] Screening page shows candidate multiselect
- [ ] **Run screening → SUCCESS (no "Unknown jd_id" error)**

### Extended Path (Should Pass)
- [ ] PDF upload works
- [ ] DOCX upload works
- [ ] TXT upload works
- [ ] Mixed format upload works
- [ ] Large batch upload (50+ docs) works
- [ ] IDs persist across page navigation
- [ ] RBAC permissions enforced

### Edge Cases (Nice to Pass)
- [ ] No uploads → warning shown
- [ ] Empty file upload → error shown
- [ ] Duplicate ID upload → handled correctly
- [ ] Concurrent uploads → no data loss
- [ ] Logout/login → documents still available

---

## Common Issues & Solutions

### Issue: Dropdown shows no options
**Cause:** No documents uploaded yet  
**Fix:** Upload via 2_Uploads.py first

### Issue: "Failed to fetch uploaded JDs"  
**Cause:** Backend not running  
**Fix:** Start backend: `python -m backend.main`

### Issue: Dropdown shows old data after upload
**Cause:** Frontend cache issue  
**Fix:** Hard refresh (Ctrl+Shift+R) or restart Streamlit

### Issue: Screening still fails with "Unknown jd_id"
**Cause:** Backend endpoints not implemented  
**Fix:** Check main.py has the new GET endpoints

---

## Success Metrics

✅ **All tests pass** → Bug is FIXED  
✅ **No "Unknown jd_id" errors** → System is working  
✅ **Dropdown shows actual documents** → Integration is complete  
✅ **Screening results appear** → End-to-end flow works  

---

**Bottom Line:** If you can run screening and see results (instead of the "Unknown jd_id" error), the bug is fixed! 🎉
