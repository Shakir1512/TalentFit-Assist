"""
Configuration management for TalentFit Assist
"""

from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    """Application settings"""
    
    # API Configuration
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # JWT Configuration
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_HOURS: int = 24
    
    # Database Configuration
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://user:password@localhost/talentfit"
    )
    
    # ChromaDB Configuration
    CHROMADB_PATH: str = os.getenv("CHROMADB_PATH", ".chroma")
    CHROMADB_COLLECTION_JDS: str = "jd_chunks"
    CHROMADB_COLLECTION_RESUMES: str = "resume_chunks"
    CHROMADB_COLLECTION_POLICIES: str = "policy_chunks"
    
    # MCP Server Configuration
    MCP_SERVER_URL: str = os.getenv("MCP_SERVER_URL", "http://localhost:8001")
    MCP_API_KEY: str = os.getenv("MCP_API_KEY", "mcp-key")
    
    # LLM Configuration
    LLM_MODEL: str = os.getenv("LLM_MODEL", "claude-3-sonnet-20240229")
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "anthropic")
    LLM_TEMPERATURE: float = 0.3
    LLM_MAX_TOKENS: int = 300
    
    # Embedding Configuration
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    EMBEDDING_DIMENSION: int = 1536
    
    # Document Configuration
    DEFAULT_CHUNK_SIZE: int = 256
    DEFAULT_CHUNK_OVERLAP: int = 50
    MAX_DOCUMENT_SIZE_MB: int = 10
    
    # Scoring Configuration
    WEIGHT_MUST_HAVE: float = 0.4
    WEIGHT_NICE_TO_HAVE: float = 0.2
    WEIGHT_EXPERIENCE: float = 0.2
    WEIGHT_DOMAIN: float = 0.1
    WEIGHT_AMBIGUITY: float = 0.1
    
    # Guardrails Configuration
    GUARDRAIL_STRICTNESS: str = os.getenv("GUARDRAIL_STRICTNESS", "HIGH")
    MAX_INPUT_TOKENS: int = 2000
    MAX_OUTPUT_TOKENS: int = 500
    MIN_OUTPUT_TOKENS: int = 50
    
    # Budget Configuration
    MONTHLY_TOKEN_BUDGET: int = int(os.getenv("MONTHLY_TOKEN_BUDGET", "1000000"))
    COST_LIMIT_USD: float = float(os.getenv("COST_LIMIT_USD", "500"))
    
    # CORS Configuration
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8501",  # Streamlit
        "http://localhost",
    ]
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
