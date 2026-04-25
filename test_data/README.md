# Test Data for TalentFit Assist

This folder contains sample test data to help you test the screening system. You can upload these files through the Streamlit UI.

## Files Included

### 1. `sample_jds.csv` - Job Descriptions
Contains 5 sample job postings:
- **jd_001**: Senior Backend Engineer (retail tech) - 5-10 years
- **jd_002**: Full Stack Developer (e-commerce) - 3-6 years
- **jd_003**: Data Engineer (analytics) - 4-8 years
- **jd_004**: DevOps Engineer (cloud infra) - 3-7 years
- **jd_005**: QA Automation Engineer - 2-5 years

**Columns:**
- jd_id: Unique job identifier
- title: Job title
- company: Company name
- content: Full job description
- must_have_skills: Critical skills (semicolon-separated)
- nice_to_have_skills: Optional skills (semicolon-separated)
- required_years_min/max: Experience range
- domain: Industry domain

### 2. `sample_resumes.csv` - Candidate Resumes
Contains 10 sample candidate profiles:
- **cand_001**: Alice Chen - Senior Backend Engineer (7 years) ⭐ Strong match for jd_001
- **cand_002**: Bob Martinez - Full Stack Dev (4 years) ⭐ Good match for jd_002
- **cand_003**: Carol Johnson - Data Engineer (6 years) ⭐ Strong match for jd_003
- **cand_004**: David Kim - DevOps Engineer (5 years) ⭐ Strong match for jd_004
- **cand_005**: Eva Rodriguez - QA Automation (3 years) ⭐ Good match for jd_005
- **cand_006**: Frank Wilson - Junior Backend (2 years) ❌ Below experience threshold for senior roles
- **cand_007**: Grace Lee - Senior Frontend (8 years) ⚠️ Wrong domain, needs backend skills
- **cand_008**: Henry Brown - Data Analyst → Engineer (3 years) ⚠️ Transitioning, missing key tools
- **cand_009**: Iris Chen - Platform Engineer (9 years) ⭐⭐ Excellent candidate for multiple roles
- **cand_010**: Jack Thompson - QA Lead (6 years) ✓ Perfect for jd_005, wrong domain for others

**Columns:**
- candidate_id: Unique candidate identifier
- name: Full name
- email: Email address
- content: Full resume/experience narrative
- skills: Skills (semicolon-separated)
- years_of_experience: Total years in field
- domain: Industry domain
- education: Degree and institution

### 3. `sample_policy.txt` - Fairness Policy
Comprehensive fairness and non-discrimination policy that defines:
- Protected attributes to exclude (age, gender, race, etc.)
- Evidence-based evaluation criteria
- Prohibited and required practices
- Data protection measures
- Compliance monitoring procedures

### 4. PDF Files (Auto-Generated)
Pre-generated PDF versions ready for upload testing:

**Job Description PDFs:**
- `jd_jd_001.pdf` - Senior Backend Engineer
- `jd_jd_002.pdf` - Full Stack Developer
- `jd_jd_003.pdf` - Data Engineer
- `jd_jd_004.pdf` - DevOps Engineer
- `jd_jd_005.pdf` - QA Automation Engineer

**Resume PDFs:**
- `resume_cand_001.pdf` through `resume_cand_010.pdf` - All 10 candidate profiles

All PDFs are text-based and fully extractable by the system.

## How to Use

### Option 1: Upload via Streamlit UI (Recommended)

You can test with **CSV files** or **PDF files** - both work!

**With CSV Files:**
1. Start the Streamlit app:
   ```bash
   streamlit run frontend/main.py --server.port 8501
   ```

2. Login as Recruiter or Admin (use demo credentials)

3. Go to **📄 Document Uploads** tab

4. **Upload Job Descriptions:**
   - Click "📋 Job Descriptions" tab
   - Upload `sample_jds.csv`
   - Click "🚀 Upload Job Descriptions"

5. **Upload Resumes:**
   - Click "👤 Resumes" tab
   - Upload `sample_resumes.csv`
   - Click "🚀 Upload Resumes"

6. **Upload Policy:**
   - Click "⚖️ Policy" tab
   - Upload `sample_policy.txt`
   - Click "🚀 Upload Policy"

**With PDF Files (Also Supported!):**
- Instead of CSV, upload the generated PDF files
- Upload `jd_jd_001.pdf` for Job Descriptions tab
- Upload `resume_cand_001.pdf` (or any resume PDF) for Resumes tab
- Upload `sample_policy.txt` for Policy tab
- The system will extract text and process normally

**Mixed Format Testing:**
- Test with CSV on first run
- Upload PDFs on second run
- Both produce identical results!

### Option 2: Direct API Upload (curl)

```bash
# Upload JDs
curl -X POST http://localhost:8000/upload/jd \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d @sample_jds.json

# Upload Resumes
curl -X POST http://localhost:8000/upload/resume \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d @sample_resumes.json

# Upload Policy
curl -X POST http://localhost:8000/upload/policy \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d @sample_policy.json
```

## Testing Scenarios

### Scenario 1: Perfect Match
- Upload all JDs and Resumes
- Run screening for jd_001 with candidates: cand_001, cand_009
- **Expected:** cand_001 and cand_009 both score 0.85+

### Scenario 2: Mixed Results
- Run screening for jd_001 with candidates: cand_001, cand_006, cand_007
- **Expected:** 
  - cand_001: 0.85+ (perfect match)
  - cand_006: 0.40-0.50 (junior, below threshold)
  - cand_007: 0.30-0.40 (wrong domain, lacks key skills)

### Scenario 3: Career Transition
- Run screening for jd_003 with candidates: cand_003, cand_008, cand_010
- **Expected:**
  - cand_003: 0.90+ (expert match)
  - cand_008: 0.50-0.60 (transitioning, learning curve)
  - cand_010: 0.10-0.20 (QA, no data skills)

### Scenario 4: Versatile Candidate
- Run screening for jd_001 and jd_004 with candidate: cand_009
- **Expected:** High match (0.80+) for both roles

## Test Data Characteristics

✅ **Realistic**: Based on actual job market requirements
✅ **Diverse**: Multiple domains, experience levels, backgrounds
✅ **Educational**: Clear skill gaps and alignment patterns
✅ **Compliant**: No protected attributes in scoring data
✅ **Auditable**: Detailed experience narratives for transparency

## Modifying Test Data

Feel free to:
- Add new candidates to `sample_resumes.csv`
- Create new job descriptions in `sample_jds.csv`
- Update the policy in `sample_policy.txt`
- Export your own screening results for analysis

## Notes

- All test data is fictional and for demonstration only
- **CSV files:** Easy to modify and reuse, good for quick testing
- **PDF files:** Pre-generated from CSV data, fully text-extractable, professional format
- The system supports TXT, PDF, and CSV formats equally
- All formats produce identical screening results
- Candidate IDs and Job IDs must match when running screenings
- Use consistent formats when modifying CSV files
- The system strips protected attributes automatically (if present)
- PDF parsing requires PyPDF2 (automatically installed)

## Support

For issues with test data or screening results:
1. Check the audit logs in the UI
2. Review cost/token usage in the dashboard
3. Contact the development team with screening ID

---

**Last Updated:** April 26, 2026
**Version:** 1.0
