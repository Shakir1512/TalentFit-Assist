#!/usr/bin/env python
"""
Generate PDF test files from CSV data.
Run this script to create sample JD and Resume PDFs for testing.

Requirements:
    pip install reportlab pandas
"""

import os
from pathlib import Path
import csv

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
    from reportlab.lib import colors
    PDF_LIBS_AVAILABLE = True
except ImportError:
    PDF_LIBS_AVAILABLE = False
    print("⚠️ PDF libraries not installed. Run: pip install reportlab")


def generate_jd_pdfs():
    """Generate PDF files for each job description from sample_jds.csv"""
    if not PDF_LIBS_AVAILABLE:
        return
    
    csv_file = Path("sample_jds.csv")
    if not csv_file.exists():
        print(f"❌ {csv_file} not found")
        return
    
    print("📝 Generating Job Description PDFs...")
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            jd_id = row['jd_id']
            title = row['title']
            company = row['company']
            content = row['content']
            must_have = row['must_have_skills']
            nice_to_have = row['nice_to_have_skills']
            years_min = row['required_years_min']
            years_max = row['required_years_max']
            domain = row['domain']
            
            # Create PDF
            pdf_filename = f"jd_{jd_id}.pdf"
            doc = SimpleDocTemplate(pdf_filename, pagesize=letter)
            styles = getSampleStyleSheet()
            
            # Custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                textColor=colors.HexColor('#1f77b4'),
                spaceAfter=12,
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=12,
                textColor=colors.HexColor('#333'),
                spaceAfter=6,
                spaceBefore=12,
            )
            
            story = []
            story.append(Paragraph(title, title_style))
            story.append(Paragraph(f"Company: {company}", styles['Normal']))
            story.append(Paragraph(f"ID: {jd_id} | Domain: {domain}", styles['Normal']))
            story.append(Spacer(1, 0.3*inch))
            
            story.append(Paragraph("Job Description", heading_style))
            story.append(Paragraph(content, styles['Normal']))
            story.append(Spacer(1, 0.2*inch))
            
            story.append(Paragraph("Requirements", heading_style))
            story.append(Paragraph(f"<b>Must-Have Skills:</b> {must_have}", styles['Normal']))
            story.append(Paragraph(f"<b>Nice-to-Have Skills:</b> {nice_to_have}", styles['Normal']))
            story.append(Paragraph(f"<b>Experience Required:</b> {years_min}-{years_max} years", styles['Normal']))
            
            doc.build(story)
            print(f"✅ Created {pdf_filename}")


def generate_resume_pdfs():
    """Generate PDF files for each resume from sample_resumes.csv"""
    if not PDF_LIBS_AVAILABLE:
        return
    
    csv_file = Path("sample_resumes.csv")
    if not csv_file.exists():
        print(f"❌ {csv_file} not found")
        return
    
    print("📝 Generating Resume PDFs...")
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            candidate_id = row['candidate_id']
            name = row['name']
            email = row['email']
            content = row['content']
            skills = row['skills']
            years = row['years_of_experience']
            domain = row['domain']
            education = row['education']
            
            # Create PDF
            pdf_filename = f"resume_{candidate_id}.pdf"
            doc = SimpleDocTemplate(pdf_filename, pagesize=letter)
            styles = getSampleStyleSheet()
            
            # Custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                textColor=colors.HexColor('#1f77b4'),
                spaceAfter=12,
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=12,
                textColor=colors.HexColor('#333'),
                spaceAfter=6,
                spaceBefore=12,
            )
            
            story = []
            story.append(Paragraph(name, title_style))
            story.append(Paragraph(f"Email: {email} | ID: {candidate_id}", styles['Normal']))
            story.append(Paragraph(f"Years of Experience: {years} | Domain: {domain}", styles['Normal']))
            story.append(Spacer(1, 0.2*inch))
            
            story.append(Paragraph("Education", heading_style))
            story.append(Paragraph(education, styles['Normal']))
            story.append(Spacer(1, 0.2*inch))
            
            story.append(Paragraph("Skills", heading_style))
            story.append(Paragraph(skills.replace(';', ', '), styles['Normal']))
            story.append(Spacer(1, 0.2*inch))
            
            story.append(Paragraph("Professional Summary", heading_style))
            story.append(Paragraph(content, styles['Normal']))
            
            doc.build(story)
            print(f"✅ Created {pdf_filename}")


def main():
    print("🚀 PDF Test Data Generator")
    print("=" * 50)
    
    if not PDF_LIBS_AVAILABLE:
        print("❌ PDF libraries not available")
        print("Install with: pip install reportlab")
        return
    
    original_dir = os.getcwd()
    test_data_dir = Path(__file__).parent
    os.chdir(test_data_dir)
    
    try:
        generate_jd_pdfs()
        print()
        generate_resume_pdfs()
        print()
        print("=" * 50)
        print("✅ All PDF files generated successfully!")
        print("📁 Files created in: test_data/")
        print()
        print("📝 Next steps:")
        print("1. Start Streamlit: streamlit run frontend/main.py")
        print("2. Go to Document Uploads")
        print("3. Upload the generated PDF files")
    finally:
        os.chdir(original_dir)


if __name__ == "__main__":
    main()
