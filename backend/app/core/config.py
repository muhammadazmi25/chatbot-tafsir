"""
Configuration for Chatbot Tafsir Ath-Thabari.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from current dir or any parent up to 5 levels
env_path = Path('.env').resolve()
if not env_path.exists():
    for parent in Path(__file__).resolve().parents:
        potential = parent / '.env'
        if potential.exists():
            env_path = potential
            break
load_dotenv(env_path, override=True)


class Settings:
    SERVICE_NAME: str = "chatbot-tafsir"
    SERVICE_PORT: int = int(os.getenv("SERVICE_PORT", "8001"))

    # MySQL
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://root:@localhost:3306/alquran"
    )

    # Qdrant
    QDRANT_URL: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    QDRANT_API_KEY: str = os.getenv("QDRANT_API_KEY", "")
    QDRANT_COLLECTION: str = os.getenv("QDRANT_COLLECTION", "tafsir_ath_thabari_hud_annur_v17")

    # Embedding — BAAI/bge-m3 (local)
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
    EMBEDDING_DIM: int = int(os.getenv("EMBEDDING_DIM", "1024"))

    # LLM — OpenRouter primary
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-exp:free")

    # Gemini fallback
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    # CORS
    CORS_ORIGINS: str = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://localhost:5173"
    )

    @property
    def cors_origins_list(self) -> list:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    # RAG Pipeline
    ENABLE_RERANKER: bool = os.getenv("ENABLE_RERANKER", "true").lower() == "true"
    RERANKER_MODEL: str = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")
    RERANKER_TOP_K: int = int(os.getenv("RERANKER_TOP_K", "10"))

    ENABLE_HYBRID_SEARCH: bool = os.getenv("ENABLE_HYBRID_SEARCH", "true").lower() == "true"
    BM25_WEIGHT: float = float(os.getenv("BM25_WEIGHT", "0.3"))
    SEMANTIC_WEIGHT: float = float(os.getenv("SEMANTIC_WEIGHT", "0.7"))
    RRF_K: int = int(os.getenv("RRF_K", "60"))
    INITIAL_RETRIEVAL_K: int = int(os.getenv("INITIAL_RETRIEVAL_K", "50"))

    ENABLE_QUERY_EXPANSION: bool = os.getenv("ENABLE_QUERY_EXPANSION", "true").lower() == "true"
    ENABLE_HYDE: bool = os.getenv("ENABLE_HYDE", "true").lower() == "true"
    ENABLE_QUERY_DECOMPOSITION: bool = os.getenv("ENABLE_QUERY_DECOMPOSITION", "false").lower() == "true"

    ENABLE_RESPONSE_CACHING: bool = os.getenv("ENABLE_RESPONSE_CACHING", "true").lower() == "true"

    ENV: str = os.getenv("ENV", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Surah range
    SURAH_START: int = int(os.getenv("SURAH_START", "11"))  # Hud
    SURAH_END: int = int(os.getenv("SURAH_END", "24"))      # An-Nur


settings = Settings()
