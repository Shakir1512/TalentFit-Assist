"""
Deterministic Scoring Engine for JD-to-Resume Matching

This engine computes candidate-JD alignment scores with 100% reproducibility.
No neural networks, no randomness, fully auditable.
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import re
from enum import Enum


class SkillMatch(Enum):
    """Skill match categories"""
    EXACT = 1.0
    PARTIAL = 0.6
    NOT_FOUND = 0.0


@dataclass
class ScoreBreakdown:
    """Detailed score breakdown for auditability"""
    must_have_match: float  # [0-100]
    nice_to_have_match: float  # [0-100]
    experience_match: float  # [0-100]
    domain_relevance: float  # [0-100]
    ambiguity_penalty: float  # [0, 50]
    final_score: float  # [0-100]
    
    audit_trail: Dict[str, str]  # Why each component scored as it did


@dataclass
class ScoringWeights:
    """Configuration weights (UI-editable)"""
    weight_must_have: float = 0.4
    weight_nice_to_have: float = 0.2
    weight_experience: float = 0.2
    weight_domain: float = 0.1
    weight_ambiguity_penalty: float = 0.1
    
    def validate(self) -> bool:
        """Ensure weights sum to 1.0"""
        total = (
            self.weight_must_have +
            self.weight_nice_to_have +
            self.weight_experience +
            self.weight_domain +
            self.weight_ambiguity_penalty
        )
        # Allow small floating point error
        return 0.99 <= total <= 1.01


@dataclass
class JobDescription:
    """Extracted JD features"""
    jd_id: str
    title: str
    must_have_skills: List[str]  # Required skills
    nice_to_have_skills: List[str]  # Preferred skills
    required_years_min: float  # Min years of experience
    required_years_max: float  # Max years (or 0 if no max)
    domain: str  # Industry/domain (e.g., "retail technology")


@dataclass
class Resume:
    """Extracted resume features"""
    candidate_id: str
    name: str
    mentioned_skills: List[str]  # All mentioned skills
    years_of_experience: float  # Total years
    domain_experience: Dict[str, float]  # {domain: years}
    ambiguity_flags: List[str]  # Data quality issues


class DeterministicScoringEngine:
    """
    Compute candidate-JD match scores deterministically.
    
    Scoring Formula:
        FINAL_SCORE = (
            (must_have_match * w_must) +
            (nice_to_have_match * w_nice) +
            (experience_match * w_exp) +
            (domain_match * w_domain) -
            (ambiguity_penalty * w_ambiguity)
        ) / 100
    
    Result: Float in [0.0, 1.0]
    """
    
    def __init__(self, weights: ScoringWeights):
        if not weights.validate():
            raise ValueError("Weights must sum to 1.0")
        self.weights = weights
    
    def compute_score(
        self,
        jd: JobDescription,
        resume: Resume
    ) -> ScoreBreakdown:
        """
        Compute candidate-JD match score.
        
        Args:
            jd: Extracted job description features
            resume: Extracted resume features
            
        Returns:
            ScoreBreakdown with components and audit trail
        """
        
        # Component 1: Must-have skills match
        must_have_match = self._compute_skill_match(
            required=jd.must_have_skills,
            available=resume.mentioned_skills,
            skill_type="MUST_HAVE"
        )
        
        # Component 2: Nice-to-have skills match
        nice_to_have_match = self._compute_skill_match(
            required=jd.nice_to_have_skills,
            available=resume.mentioned_skills,
            skill_type="NICE_TO_HAVE"
        )
        
        # Component 3: Experience range alignment
        experience_match = self._compute_experience_match(
            jd_min_years=jd.required_years_min,
            jd_max_years=jd.required_years_max,
            resume_years=resume.years_of_experience
        )
        
        # Component 4: Domain relevance
        domain_relevance = self._compute_domain_match(
            required_domain=jd.domain,
            domain_experience=resume.domain_experience
        )
        
        # Component 5: Ambiguity penalty
        ambiguity_penalty = self._compute_ambiguity_penalty(
            ambiguity_flags=resume.ambiguity_flags
        )
        
        # Build audit trail
        audit_trail = {
            "must_have_match": f"{must_have_match:.1f}% ({len([s for s in jd.must_have_skills if self._skill_match(s, resume.mentioned_skills) > 0])}/{len(jd.must_have_skills)} skills matched)",
            "nice_to_have_match": f"{nice_to_have_match:.1f}% ({len([s for s in jd.nice_to_have_skills if self._skill_match(s, resume.mentioned_skills) > 0])}/{len(jd.nice_to_have_skills)} skills matched)",
            "experience_match": f"{experience_match:.1f}% (Resume: {resume.years_of_experience} years, Required: {jd.required_years_min}-{jd.required_years_max})",
            "domain_relevance": f"{domain_relevance:.1f}% ({jd.domain} experience: {resume.domain_experience.get(jd.domain, 0)} years)",
            "ambiguity_penalty": f"{ambiguity_penalty:.1f} points ({len(resume.ambiguity_flags)} quality issues)"
        }
        
        # Final score computation
        final_score = (
            (must_have_match * self.weights.weight_must_have) +
            (nice_to_have_match * self.weights.weight_nice_to_have) +
            (experience_match * self.weights.weight_experience) +
            (domain_relevance * self.weights.weight_domain) -
            (ambiguity_penalty * self.weights.weight_ambiguity_penalty)
        ) / 100
        
        # Clamp to [0, 1]
        final_score = max(0.0, min(1.0, final_score))
        
        return ScoreBreakdown(
            must_have_match=must_have_match,
            nice_to_have_match=nice_to_have_match,
            experience_match=experience_match,
            domain_relevance=domain_relevance,
            ambiguity_penalty=ambiguity_penalty,
            final_score=final_score,
            audit_trail=audit_trail
        )
    
    def _compute_skill_match(
        self,
        required: List[str],
        available: List[str],
        skill_type: str
    ) -> float:
        """
        Compute % of required skills found in resume.
        
        Args:
            required: List of required skills
            available: List of mentioned skills in resume
            skill_type: For audit logging
            
        Returns:
            Match percentage [0-100]
        """
        if not required:
            return 100.0  # No requirements = 100% match
        
        matches = sum(
            1 for skill in required
            if self._skill_match(skill, available) > 0
        )
        
        return (matches / len(required)) * 100
    
    def _skill_match(self, required_skill: str, available_skills: List[str]) -> float:
        """
        Check if required skill is mentioned in available skills.
        Case-insensitive, partial matches allowed.
        
        Args:
            required_skill: Single requirement
            available_skills: List to search
            
        Returns:
            Match score: 1.0 (exact), 0.6 (partial), 0.0 (not found)
        """
        required_lower = required_skill.lower()
        
        for available in available_skills:
            available_lower = available.lower()
            
            # Exact match
            if required_lower == available_lower:
                return SkillMatch.EXACT.value
            
            # Partial match (substring)
            if required_lower in available_lower or available_lower in required_lower:
                return SkillMatch.PARTIAL.value
        
        return SkillMatch.NOT_FOUND.value
    
    def _compute_experience_match(
        self,
        jd_min_years: float,
        jd_max_years: float,
        resume_years: float
    ) -> float:
        """
        Score based on experience alignment with requirements.
        
        Logic:
        - Too junior: Linear penalty
        - Within range: 100%
        - Overqualified: -5% per extra year (diminishing return)
        
        Args:
            jd_min_years: Minimum required years
            jd_max_years: Maximum preferred years (0 = no max)
            resume_years: Candidate's years
            
        Returns:
            Match score [0-100]
        """
        # Too junior
        if resume_years < jd_min_years:
            shortage = jd_min_years - resume_years
            return max(0.0, 100 - (shortage * 20))  # -20% per year short
        
        # Within range or within 5 years above max
        if jd_max_years == 0 or resume_years <= jd_max_years + 5:
            return 100.0
        
        # Significantly overqualified
        excess = resume_years - (jd_max_years + 5)
        return max(50.0, 100 - (excess * 5))  # -5% per excess year, floor at 50%
    
    def _compute_domain_match(
        self,
        required_domain: str,
        domain_experience: Dict[str, float]
    ) -> float:
        """
        Score based on domain relevance.
        
        Logic:
        - Direct domain experience: 100%
        - Related domain (retail vs tech): 70%
        - No domain experience: 30%
        - Any experience > 0: Minimum 30% (some transfer learning)
        
        Args:
            required_domain: Required domain
            domain_experience: {domain: years}
            
        Returns:
            Domain match score [0-100]
        """
        required_lower = required_domain.lower()
        
        # Direct match
        if required_lower in domain_experience:
            years = domain_experience[required_lower]
            if years > 0:
                return 100.0
        
        # Check for related domains
        related_domains = {
            "retail": ["retail technology", "e-commerce", "omnichannel"],
            "technology": ["retail technology", "tech", "software"],
            "finance": ["fintech", "financial"],
        }
        
        for domain, years in domain_experience.items():
            if years > 0:
                # Any relevant experience: 70%
                if any(req in domain.lower() or domain.lower() in req
                       for req in related_domains.get(required_lower, [required_lower])):
                    return 70.0
        
        # Any experience (even other domain): 30%
        if any(years > 0 for years in domain_experience.values()):
            return 30.0
        
        # No domain experience
        return 0.0
    
    def _compute_ambiguity_penalty(self, ambiguity_flags: List[str]) -> float:
        """
        Penalty for data quality/clarity issues.
        
        Each flag reduces score by fixed amount:
        - Missing years of experience: -10
        - Gaps in resume: -5
        - Unclear skill names: -5
        - No education listed: -5
        
        Max penalty: 50 points
        
        Args:
            ambiguity_flags: Quality issues found
            
        Returns:
            Penalty amount [0-50]
        """
        penalty_map = {
            "missing_years": 10,
            "resume_gaps": 5,
            "unclear_skills": 5,
            "no_education": 5,
        }
        
        total_penalty = sum(penalty_map.get(flag, 0) for flag in ambiguity_flags)
        
        return min(50.0, total_penalty)


# Example usage
if __name__ == "__main__":
    # Initialize engine with weights
    weights = ScoringWeights(
        weight_must_have=0.4,
        weight_nice_to_have=0.2,
        weight_experience=0.2,
        weight_domain=0.1,
        weight_ambiguity_penalty=0.1
    )
    engine = DeterministicScoringEngine(weights)
    
    # Create sample data
    jd = JobDescription(
        jd_id="jd_001",
        title="Senior Software Engineer",
        must_have_skills=["Python", "PostgreSQL", "REST APIs"],
        nice_to_have_skills=["Kubernetes", "Terraform"],
        required_years_min=5.0,
        required_years_max=10.0,
        domain="retail technology"
    )
    
    resume = Resume(
        candidate_id="c_042",
        name="Alice Chen",
        mentioned_skills=["Python", "PostgreSQL", "Django", "Docker"],
        years_of_experience=6.5,
        domain_experience={"retail technology": 4.0, "fintech": 2.5},
        ambiguity_flags=[]
    )
    
    # Compute score
    breakdown = engine.compute_score(jd, resume)
    
    print(f"Candidate: {resume.name}")
    print(f"Final Score: {breakdown.final_score:.2f} ({breakdown.final_score * 100:.1f}%)")
    print("\nBreakdown:")
    for component, value in breakdown.audit_trail.items():
        print(f"  {component}: {value}")
