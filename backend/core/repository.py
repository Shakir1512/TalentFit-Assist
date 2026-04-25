"""
Local repository and retrieval facade for TalentFit Assist.

This module is intentionally small and deterministic for the local MVP. It keeps
the same domain boundaries used in production: ingestion cleans data, chunking
adds metadata, retrieval is evidence-only, and scoring consumes structured
features rather than LLM output.
"""

from __future__ import annotations

import json
import math
import re
import uuid
from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from backend.core.data_cleaner import ProtectedAttributeCleaner
from backend.core.scoring_engine import JobDescription, Resume, ScoreBreakdown


DEFAULT_CONFIG: Dict[str, Any] = {
    "llm_model": "gpt-4o-mini",
    "provider": "openai",
    "temperature": 0.2,
    "max_tokens": 500,
    "embedding_model": "text-embedding-3-small",
    "top_k": 5,
    "guardrail_strictness": "HIGH",
    "monthly_token_budget": 500_000,
    "chunking": {
        "jd": {"chunk_size": 900, "overlap": 120},
        "resume": {"chunk_size": 800, "overlap": 100},
        "policy": {"chunk_size": 700, "overlap": 80},
    },
    "scoring_weights": {
        "must_have": 0.4,
        "nice_to_have": 0.2,
        "experience": 0.2,
        "domain": 0.1,
        "ambiguity": 0.1,
    },
}


def utc_now() -> str:
    return datetime.utcnow().isoformat()


def parse_jsonl(payload: str) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for line_number, line in enumerate(payload.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSONL on line {line_number}: {exc.msg}") from exc
    return records


def chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    overlap = max(0, min(overlap, chunk_size - 1))
    chunks: List[str] = []
    cursor = 0
    while cursor < len(text):
        chunks.append(text[cursor : cursor + chunk_size])
        cursor += chunk_size - overlap
    return chunks or [text]


def normalize_terms(text: str) -> set[str]:
    stop_words = {
        "and",
        "or",
        "the",
        "for",
        "with",
        "from",
        "that",
        "this",
        "role",
        "team",
        "work",
        "years",
        "experience",
    }
    return {
        token
        for token in re.findall(r"[a-zA-Z][a-zA-Z0-9+#.-]{1,}", text.lower())
        if token not in stop_words
    }


def lexical_similarity(left: str, right: str) -> float:
    left_terms = normalize_terms(left)
    right_terms = normalize_terms(right)
    if not left_terms or not right_terms:
        return 0.0
    intersection = left_terms.intersection(right_terms)
    denominator = math.sqrt(len(left_terms) * len(right_terms))
    return round(len(intersection) / denominator, 4)


def _as_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in re.split(r"[,;\n]", value) if item.strip()]
    return [str(value)]


def extract_years(text: str) -> float:
    matches = re.findall(r"(\d+(?:\.\d+)?)\+?\s*(?:years|yrs|year)\b", text, re.IGNORECASE)
    if not matches:
        return 0.0
    return max(float(match) for match in matches)


def infer_skills(text: str) -> List[str]:
    known_skills = [
        "python",
        "java",
        "javascript",
        "typescript",
        "react",
        "fastapi",
        "django",
        "postgresql",
        "mysql",
        "mongodb",
        "rest api",
        "rest apis",
        "kubernetes",
        "docker",
        "terraform",
        "aws",
        "azure",
        "gcp",
        "spark",
        "airflow",
        "machine learning",
        "data engineering",
        "streamlit",
    ]
    text_lower = text.lower()
    return sorted({skill for skill in known_skills if skill in text_lower})


class InMemoryTalentRepository:
    """
    Local deterministic repository.

    Production replacement:
    - PostgreSQL for configs, audit, screening results
    - S3 or encrypted object storage for original documents
    - Persistent ChromaDB for embeddings and metadata-filtered retrieval
    """

    def __init__(self) -> None:
        self.config: Dict[str, Any] = json.loads(json.dumps(DEFAULT_CONFIG))
        self.documents: Dict[str, Dict[str, Dict[str, Any]]] = {
            "jd": {},
            "resume": {},
            "policy": {},
        }
        self.chunks: List[Dict[str, Any]] = []
        self.screenings: Dict[str, Dict[str, Any]] = {}
        self.audit_logs: List[Dict[str, Any]] = []
        self.token_usage: List[Dict[str, Any]] = []

    def update_config(self, patch: Dict[str, Any]) -> Dict[str, Any]:
        for key, value in patch.items():
            if key == "scoring_weights":
                self.config["scoring_weights"].update(value)
            elif key in {"chunk_size", "chunk_overlap"}:
                target = "chunk_size" if key == "chunk_size" else "overlap"
                for chunk_cfg in self.config["chunking"].values():
                    chunk_cfg[target] = int(value)
            elif key in self.config:
                self.config[key] = value
        return self.config

    def ingest_records(self, kind: str, records: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
        cleaner = ProtectedAttributeCleaner(strict_mode=True)
        processed: Dict[str, Any] = {}
        for record in records:
            doc_id = self._document_id(kind, record)
            raw_text = str(record.get("content") or record.get("text") or record.get("description") or "")
            if not raw_text:
                raise ValueError(f"{kind} record {doc_id} is missing content/text")

            cleaned_text, actions = cleaner.clean_document(raw_text)
            document = {
                **record,
                "id": doc_id,
                "kind": kind,
                "cleaned_text": cleaned_text,
                "cleaning_actions": [asdict(action) for action in actions],
                "uploaded_at": utc_now(),
            }
            self.documents[kind][doc_id] = document
            self._replace_chunks(kind, doc_id, cleaned_text)
            processed[doc_id] = {
                "chunks": len([chunk for chunk in self.chunks if chunk["metadata"]["document_id"] == doc_id]),
                "cleaning_actions": len(actions),
                "embedded": True,
            }
        return processed

    def ingest_policy_markdown(self, content: str, policy_id: str = "policy_default") -> Dict[str, Any]:
        return self.ingest_records(
            "policy",
            [{"policy_id": policy_id, "content": content, "title": policy_id}],
        )

    def _document_id(self, kind: str, record: Dict[str, Any]) -> str:
        keys = {
            "jd": ["jd_id", "id"],
            "resume": ["candidate_id", "resume_id", "id"],
            "policy": ["policy_id", "id"],
        }[kind]
        for key in keys:
            if record.get(key):
                return str(record[key])
        return f"{kind}_{uuid.uuid4().hex[:8]}"

    def _replace_chunks(self, kind: str, doc_id: str, text: str) -> None:
        self.chunks = [chunk for chunk in self.chunks if chunk["metadata"]["document_id"] != doc_id]
        cfg = self.config["chunking"][kind]
        for index, chunk in enumerate(chunk_text(text, int(cfg["chunk_size"]), int(cfg["overlap"]))):
            self.chunks.append(
                {
                    "chunk_id": f"{kind}_{doc_id}_{index}",
                    "text": chunk,
                    "metadata": {
                        "document_id": doc_id,
                        "candidate_id": doc_id if kind == "resume" else None,
                        "jd_id": doc_id if kind == "jd" else None,
                        "section_type": kind,
                        "chunk_index": index,
                        "embedding_model": self.config["embedding_model"],
                    },
                }
            )

    def jd_features(self, jd_id: str) -> JobDescription:
        record = self.documents["jd"].get(jd_id)
        if not record:
            raise KeyError(f"Unknown jd_id: {jd_id}")
        text = record["cleaned_text"]
        years = float(record.get("required_years_min") or record.get("min_years") or extract_years(text) or 0)
        return JobDescription(
            jd_id=jd_id,
            title=str(record.get("title") or "Untitled role"),
            must_have_skills=_as_list(record.get("must_have_skills")) or infer_skills(text)[:5],
            nice_to_have_skills=_as_list(record.get("nice_to_have_skills")),
            required_years_min=years,
            required_years_max=float(record.get("required_years_max") or record.get("max_years") or 0),
            domain=str(record.get("domain") or record.get("industry") or "technology").lower(),
        )

    def resume_features(self, candidate_id: str) -> Resume:
        record = self.documents["resume"].get(candidate_id)
        if not record:
            raise KeyError(f"Unknown candidate_id: {candidate_id}")
        text = record["cleaned_text"]
        domain = str(record.get("domain") or record.get("industry") or "technology").lower()
        years = float(record.get("years_of_experience") or record.get("experience_years") or extract_years(text) or 0)
        ambiguity_flags = _as_list(record.get("ambiguity_flags"))
        if years == 0:
            ambiguity_flags.append("missing_years")
        return Resume(
            candidate_id=candidate_id,
            name=str(record.get("name") or candidate_id),
            mentioned_skills=_as_list(record.get("skills")) or infer_skills(text),
            years_of_experience=years,
            domain_experience={domain: years} if domain else {},
            ambiguity_flags=ambiguity_flags,
        )

    def retrieve_evidence(self, jd_id: str, candidate_ids: List[str], top_k: int) -> List[Dict[str, Any]]:
        jd = self.documents["jd"].get(jd_id)
        if not jd:
            raise KeyError(f"Unknown jd_id: {jd_id}")
        jd_text = jd["cleaned_text"]
        results: List[Dict[str, Any]] = []
        for candidate_id in candidate_ids:
            candidate_chunks = [
                chunk for chunk in self.chunks if chunk["metadata"].get("candidate_id") == candidate_id
            ]
            ranked = sorted(
                candidate_chunks,
                key=lambda chunk: lexical_similarity(jd_text, chunk["text"]),
                reverse=True,
            )[:top_k]
            results.append(
                {
                    "candidate_id": candidate_id,
                    "chunks": [
                        {
                            **chunk,
                            "similarity": lexical_similarity(jd_text, chunk["text"]),
                        }
                        for chunk in ranked
                    ],
                }
            )
        return results

    def active_policy_text(self) -> str:
        policies = list(self.documents["policy"].values())
        return policies[-1]["cleaned_text"] if policies else "Use skills and role evidence only. Do not use protected attributes."

    def record_screening(self, payload: Dict[str, Any]) -> str:
        screening_id = f"scr_{uuid.uuid4().hex[:10]}"
        self.screenings[screening_id] = {"screening_id": screening_id, **payload, "created_at": utc_now()}
        return screening_id

    def log_audit(self, user_id: str, action: str, details: Dict[str, Any], success: bool = True) -> Dict[str, Any]:
        entry = {
            "audit_id": f"aud_{uuid.uuid4().hex[:10]}",
            "timestamp": utc_now(),
            "user_id": user_id,
            "action": action,
            "details": details,
            "success": success,
            "severity": "INFO" if success else "WARNING",
        }
        self.audit_logs.append(entry)
        return entry

    def log_usage(self, user_id: str, role: str, model: str, token_payload: Dict[str, Any]) -> None:
        self.token_usage.append(
            {
                "timestamp": utc_now(),
                "user_id": user_id,
                "role": role,
                "model": model,
                **token_payload,
            }
        )

    def monthly_tokens(self) -> int:
        return sum(int(item.get("input_tokens", 0)) + int(item.get("output_tokens", 0)) for item in self.token_usage)

    def usage_summary(self) -> Dict[str, Any]:
        total_tokens = self.monthly_tokens()
        total_cost = round(sum(float(item.get("total_cost", 0)) for item in self.token_usage), 6)
        by_role: Dict[str, int] = {}
        for item in self.token_usage:
            by_role[item["role"]] = by_role.get(item["role"], 0) + int(item.get("input_tokens", 0)) + int(item.get("output_tokens", 0))
        budget = int(self.config["monthly_token_budget"])
        return {
            "total_tokens_month": total_tokens,
            "total_cost_month": total_cost,
            "monthly_token_budget": budget,
            "budget_used_percent": round((total_tokens / budget) * 100, 2) if budget else 0,
            "cost_by_role": by_role,
            "records": self.token_usage[-50:],
        }


def score_to_dict(candidate_id: str, score: ScoreBreakdown) -> Dict[str, Any]:
    return {
        "candidate_id": candidate_id,
        "score": score.final_score,
        "breakdown": {
            "must_have_match": score.must_have_match,
            "nice_to_have_match": score.nice_to_have_match,
            "experience_match": score.experience_match,
            "domain_relevance": score.domain_relevance,
            "ambiguity_penalty": score.ambiguity_penalty,
        },
        "audit_trail": score.audit_trail,
    }
