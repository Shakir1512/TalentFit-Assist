"""
Data Cleaner - Protected Attribute Removal

Strips protected attributes at document ingestion time.
Ensures fairness by removing information that could enable bias.

Protected Attributes:
- Age / Date of birth
- Gender / Pronouns
- Nationality / Country of origin
- Institution / School names
- Graduation year
- Age-related keywords
"""

import re
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class CleaningAction:
    """Record of what was cleaned"""
    attribute_type: str
    original_text: str
    redacted_text: str
    count: int = 1


class ProtectedAttributeCleaner:
    """
    Aggressively clean documents of protected attributes.
    Applied at ingestion time; irreversible.
    """
    
    # Protected attribute patterns (case-insensitive)
    PROTECTED_PATTERNS = {
        "age_numeric": {
            "pattern": r'\b(\d{1,3})\s*(year|yo|y\.o\.|yr|years old|year old|age|yrs)\b',
            "replacement": "[AGE]",
            "description": "Numeric age"
        },
        "birth_date": {
            "pattern": r'\b(born|dob|d\.o\.b\.)\s*(?:in\s+)?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{2,4}[/-]\d{1,2}[/-]\d{1,2})',
            "replacement": "[DOB]",
            "description": "Birth date"
        },
        "graduation_year": {
            "pattern": r'\b(class of|graduated|grad|graduation year|batch)\s*:?\s*([\'"]?(19|20)\d{2}[\'"]?|[\'"](19|20)\d{2}[\'"])',
            "replacement": "[GRADUATION_YEAR]",
            "description": "Graduation year"
        },
        "gender_explicit": {
            "pattern": r'\b(male|female|man|woman|boy|girl)\b',
            "replacement": "[GENDER]",
            "description": "Explicit gender"
        },
        "gender_pronouns": {
            "pattern": r'\b(he|she|his|her|him)\b',
            "replacement": "[PRONOUN]",
            "description": "Gender pronoun"
        },
        "nationality": {
            "pattern": r'\b(Indian|American|Chinese|British|Canadian|Australian|French|German|Australian|Mexican|Nigerian|Brazilian|Japanese|Korean|Spanish|Italian|Russian|Indian|Pakistani)\b',
            "replacement": "[NATIONALITY]",
            "description": "Nationality"
        },
        "institution": {
            "pattern": r'\b(IIT|MIT|Stanford|Harvard|Oxford|Cambridge|Delhi University|NIT|BITS|Pune|Bombay|Bangalore|Caltech|Yale|Princeton|Columbia|Berkeley)\b',
            "replacement": "[INSTITUTION]",
            "description": "Educational institution"
        },
        "age_keywords": {
            "pattern": r'\b(young|fresh|fresher|junior|senior|experienced|veteran|retiree|midcareer|postgrad|fresher|new graduate)\b',
            "replacement": "[AGE_PROXY]",
            "description": "Age-proxy keywords"
        },
        "family_status": {
            "pattern": r'\b(married|single|divorced|widowed|parent|mother|father|spouse|husband|wife|children|kids|family status)\b',
            "replacement": "[FAMILY_STATUS]",
            "description": "Family status"
        },
        "religious_affiliation": {
            "pattern": r'\b(Hindu|Muslim|Christian|Jewish|Buddhist|Sikh|Catholic|Orthodox|Protestant|Atheist|Agnostic|Jain|Zoroastrian)\b',
            "replacement": "[RELIGION]",
            "description": "Religious affiliation"
        }
    }
    
    def __init__(self, strict_mode: bool = True):
        """
        Initialize cleaner.
        
        Args:
            strict_mode: If True, aggressively remove age-proxy keywords
        """
        self.strict_mode = strict_mode
        self.cleaning_actions: List[CleaningAction] = []
    
    def clean_document(self, text: str) -> Tuple[str, List[CleaningAction]]:
        """
        Clean document of all protected attributes.
        
        Args:
            text: Original document text
            
        Returns:
            (cleaned_text, list_of_actions)
        """
        self.cleaning_actions = []
        cleaned_text = text
        
        for attr_type, pattern_config in self.PROTECTED_PATTERNS.items():
            # Skip age proxies in non-strict mode
            if not self.strict_mode and "proxy" in attr_type:
                continue
            
            pattern = pattern_config["pattern"]
            replacement = pattern_config["replacement"]
            
            # Find all matches
            matches = re.finditer(pattern, cleaned_text, re.IGNORECASE)
            matches_list = list(matches)
            
            if matches_list:
                # Replace all occurrences
                cleaned_text = re.sub(
                    pattern,
                    replacement,
                    cleaned_text,
                    flags=re.IGNORECASE
                )
                
                # Record action
                self.cleaning_actions.append(CleaningAction(
                    attribute_type=attr_type,
                    original_text=pattern_config["description"],
                    redacted_text=replacement,
                    count=len(matches_list)
                ))
        
        return cleaned_text, self.cleaning_actions
    
    def get_summary(self) -> Dict[str, any]:
        """
        Get summary of what was cleaned from a document.
        
        Returns:
            Dict with cleaning statistics
        """
        return {
            "attributes_removed": len(self.cleaning_actions),
            "total_redactions": sum(a.count for a in self.cleaning_actions),
            "actions": [
                {
                    "type": a.attribute_type,
                    "count": a.count,
                    "description": a.original_text
                }
                for a in self.cleaning_actions
            ]
        }
    
    def validate_cleaned_text(self, text: str) -> Tuple[bool, List[str]]:
        """
        Validate that no obvious protected attributes remain.
        
        Args:
            text: Cleaned text to validate
            
        Returns:
            (is_clean, list_of_violations)
        """
        violations = []
        
        # Check numeric ages (even if pattern misses some)
        if re.search(r'\b([2-8]\d)\s*(year|yr|old|yo)\b', text, re.IGNORECASE):
            violations.append("Numeric age detected")
        
        # Check unredacted pronouns
        pronouns_remaining = re.findall(r'\b(he|she|his|her|him)\b', text, re.IGNORECASE)
        if len(pronouns_remaining) > 5:  # Allow some pronouns in natural speech
            violations.append(f"Excessive pronouns detected: {len(pronouns_remaining)}")
        
        # Check for graduation years (4-digit patterns that look like years)
        suspicious_years = re.findall(r'\b(19|20)\d{2}\b', text)
        # Allow current/future years, but be suspicious of others
        current_year = 2026
        for year in suspicious_years:
            year_int = int(year)
            if year_int < 2000 or year_int > current_year + 5:
                if not re.search(f'\\b{year}\\b.*\\[', text):  # Check if followed by redaction marker
                    violations.append(f"Suspicious year found: {year}")
        
        is_clean = len(violations) == 0
        
        return is_clean, violations


class DataIntegrityValidator:
    """
    Validate document structure and content quality after cleaning.
    """
    
    MIN_DOCUMENT_LENGTH = 50  # Characters
    MAX_REDACTION_RATIO = 0.3  # Max 30% of text can be redactions
    REQUIRED_SECTIONS_JD = {"title", "responsibilities", "requirements"}
    REQUIRED_SECTIONS_RESUME = {"experience", "education", "skills"}
    
    @staticmethod
    def validate_jd(raw_text: str, cleaned_text: str, metadata: Dict) -> Tuple[bool, List[str]]:
        """
        Validate job description quality.
        
        Args:
            raw_text: Original JD
            cleaned_text: Cleaned JD
            metadata: Document metadata
            
        Returns:
            (is_valid, list_of_issues)
        """
        issues = []
        
        # Check minimum length
        if len(cleaned_text) < DataIntegrityValidator.MIN_DOCUMENT_LENGTH:
            issues.append(f"JD too short: {len(cleaned_text)} chars")
        
        # Check redaction ratio
        redaction_count = len(re.findall(r'\[.*?\]', cleaned_text))
        if len(cleaned_text) > 0:
            redaction_ratio = redaction_count / len(cleaned_text)
            if redaction_ratio > DataIntegrityValidator.MAX_REDACTION_RATIO:
                issues.append(f"Too much redaction: {redaction_ratio:.1%}")
        
        # Check for required keywords
        text_lower = cleaned_text.lower()
        for section in ["responsibility", "requirement", "skill", "experience"]:
            if section not in text_lower:
                issues.append(f"Missing section indication: {section}")
        
        return len(issues) == 0, issues
    
    @staticmethod
    def validate_resume(raw_text: str, cleaned_text: str, metadata: Dict) -> Tuple[bool, List[str]]:
        """
        Validate resume quality.
        
        Args:
            raw_text: Original resume
            cleaned_text: Cleaned resume
            metadata: Resume metadata
            
        Returns:
            (is_valid, list_of_issues)
        """
        issues = []
        
        # Check minimum length
        if len(cleaned_text) < DataIntegrityValidator.MIN_DOCUMENT_LENGTH:
            issues.append(f"Resume too short: {len(cleaned_text)} chars")
        
        # Check redaction ratio
        redaction_count = len(re.findall(r'\[.*?\]', cleaned_text))
        if len(cleaned_text) > 0:
            redaction_ratio = redaction_count / len(cleaned_text)
            if redaction_ratio > DataIntegrityValidator.MAX_REDACTION_RATIO:
                issues.append(f"Too much redaction: {redaction_ratio:.1%}")
        
        # Check for required keywords
        text_lower = cleaned_text.lower()
        found_sections = sum([
            "experience" in text_lower or "work" in text_lower,
            "education" in text_lower or "degree" in text_lower,
            "skill" in text_lower or "expertise" in text_lower,
        ])
        if found_sections < 2:
            issues.append("Resume missing key sections (exp, edu, skills)")
        
        return len(issues) == 0, issues


# Example usage
if __name__ == "__main__":
    cleaner = ProtectedAttributeCleaner(strict_mode=True)
    
    # Sample document with protected attributes
    sample_resume = """
    ALICE CHEN
    DOB: 05/15/1995
    Indian National
    
    Experience:
    - Senior Software Engineer at Tech Corp (Male-dominated field)
    - 8 years of experience
    - Graduated from IIT Bombay, Class of 2018
    
    Skills: Python, PostgreSQL, REST APIs
    Married with 2 children
    Religious preference: Hindu
    """
    
    cleaned, actions = cleaner.clean_document(sample_resume)
    
    print("ORIGINAL:")
    print(sample_resume)
    print("\n" + "="*50 + "\n")
    print("CLEANED:")
    print(cleaned)
    print("\n" + "="*50 + "\n")
    print("CLEANING SUMMARY:")
    for action in actions:
        print(f"  {action.attribute_type}: {action.count} occurrences replaced with {action.redacted_text}")
    
    # Validate
    is_clean, violations = cleaner.validate_cleaned_text(cleaned)
    print(f"\nValidation: {'✓ PASS' if is_clean else '✗ FAIL'}")
    if violations:
        for v in violations:
            print(f"  Warning: {v}")
