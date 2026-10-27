"""
Chatbot Tafsir Ath-Thabari — FastAPI Entry Point
Port: 8001
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging_config import setup_logging, get_logger
from app.db.database import create_chat_tables

setup_logging()
logger = get_logger('main')


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 50)
    logger.info("Starting Chatbot Tafsir Ath-Thabari")
    logger.info(f"Port: {settings.SERVICE_PORT} | ENV: {settings.ENV}")
    logger.info("=" * 50)

    # Create chat tables if not exist
    try:
        create_chat_tables()
        logger.info("Chat tables ready (MySQL)")
    except Exception as e:
        logger.error(f"DB init error: {e}")

    # Load RAG service (loads BGE-M3 model)
    try:
        from app.services.rag_service import get_rag_service
        rag = get_rag_service()
        app.state.rag_service = rag
        logger.info("RAG service initialized with BGE-M3 + Qdrant")
    except Exception as e:
        logger.error(f"RAG init failed: {e}")
        app.state.rag_service = None

    # Pre-warm reranker model to eliminate first-query cold-start latency
    try:
        from app.services.reranker import get_reranker
        get_reranker()
        logger.info("Reranker pre-warmed successfully at startup")
    except Exception as e:
        logger.warning(f"Reranker pre-warm skipped/failed: {e}")

    yield
    logger.info("Shutting down Chatbot Tafsir Ath-Thabari")


app = FastAPI(
    title="Chatbot Tafsir Ath-Thabari",
    description="RAG Chatbot untuk Tafsir Ath-Thabari (Surah Hud–An-Nur)",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.ENV != "production" else None,
    redoc_url="/redoc" if settings.ENV != "production" else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
from app.api import chat, sessions, tafsir

app.include_router(chat.router,     prefix="/api/v1/chat",    tags=["Chat"])
app.include_router(sessions.router, prefix="/api/v1/sessions", tags=["Sessions"])
app.include_router(tafsir.router,   prefix="/api/v1/tafsir",  tags=["Tafsir"])


@app.get("/")
def root():
    return {
        "service": "chatbot-tafsir",
        "version": "1.0.0",
        "status": "running",
        "collection": settings.QDRANT_COLLECTION,
    }


@app.get("/health")
def health(request_app=None):
    from fastapi import Request
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.SERVICE_PORT)
