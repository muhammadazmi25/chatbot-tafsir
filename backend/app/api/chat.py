"""Chat API — POST /api/v1/chat & /api/v1/chat/stream"""

import json
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.logging_config import get_logger
import app.services.session_service as session_svc

logger = get_logger('api.chat')
router = APIRouter()


class ChatRequest(BaseModel):
    query: str
    session_uuid: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    session_uuid: str
    sources: List[Dict] = []


@router.post("", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    http_req: Request,
    db: Session = Depends(get_db),
):
    rag = getattr(http_req.app.state, 'rag_service', None)
    if not rag:
        raise HTTPException(503, "RAG service not ready")

    # Get or create session
    session = None
    if req.session_uuid:
        session = session_svc.get_session(db, req.session_uuid)
    if not session:
        session = session_svc.create_session(db)

    # Load conversation history (last 6 messages)
    messages = session_svc.get_session_messages(db, session.id)
    history = [
        {"role": m.role, "content": m.content}
        for m in messages[-6:]
    ]

    # Save user message
    session_svc.save_message(db, session.id, "user", req.query)

    # Auto-title session from first message
    if len(messages) == 0:
        title = req.query[:60] + ("..." if len(req.query) > 60 else "")
        session_svc.update_session_title(db, session.id, title)

    # RAG query
    try:
        result = rag.query(req.query, conversation_history=history)
    except Exception as e:
        logger.exception(f"RAG error: {e}")
        raise HTTPException(500, str(e))

    # Save assistant message
    session_svc.save_message(
        db, session.id, "assistant",
        result["answer"],
        result.get("sources", [])
    )

    return ChatResponse(
        answer=result["answer"],
        session_uuid=session.session_uuid,
        sources=result.get("sources", []),
    )


@router.post("/stream")
async def chat_stream(req: ChatRequest, http_req: Request, db: Session = Depends(get_db)):
    """SSE streaming chat endpoint."""
    rag = getattr(http_req.app.state, 'rag_service', None)
    if not rag:
        raise HTTPException(503, "RAG service not ready")

    # Get or create session
    session = None
    if req.session_uuid:
        session = session_svc.get_session(db, req.session_uuid)
    if not session:
        session = session_svc.create_session(db)

    messages = session_svc.get_session_messages(db, session.id)
    history = [{"role": m.role, "content": m.content} for m in messages[-6:]]
    session_svc.save_message(db, session.id, "user", req.query)

    if len(messages) == 0:
        title = req.query[:60] + ("..." if len(req.query) > 60 else "")
        session_svc.update_session_title(db, session.id, title)

    async def event_generator():
        full_answer = ""
        try:
            # Send session uuid first
            yield f"data: {json.dumps({'type': 'session', 'session_uuid': session.session_uuid})}\n\n"

            # ── Guard checks (same as non-stream) ────────────────────────────
            from app.services.rag_service import (
                SYSTEM_PROMPT, build_rag_context,
                _check_scope, _check_ood, _extract_user_constraints,
            )
            scope_err = _check_scope(req.query)
            if scope_err:
                full_answer = scope_err
                yield f"data: {json.dumps({'type': 'token', 'content': scope_err})}\n\n"
                return

            ood_err = _check_ood(req.query)
            if ood_err:
                full_answer = ood_err
                yield f"data: {json.dumps({'type': 'token', 'content': ood_err})}\n\n"
                return

            user_constraints = _extract_user_constraints(req.query)

            # Get docs
            docs = rag.search(req.query)
            sources = []
            seen = set()
            for doc in docs:
                src = doc.get("source", "")
                if src not in seen:
                    seen.add(src)
                    sources.append({
                        "source": src,
                        "chunk_content": doc.get("text", "")[:400],
                        "score": doc.get("reranker_score", doc.get("score", 0)),
                    })

            yield f"data: {json.dumps({'type': 'sources', 'sources': sources[:5]})}\n\n"

            # Generate answer using unified build_rag_context and SYSTEM_PROMPT
            # (SYSTEM_PROMPT, build_rag_context already imported in guard block above)
            context = build_rag_context(docs)

            history_ctx = ""
            if history:
                lines = [f"{m['role'].capitalize()}: {m['content']}" for m in history[-4:]]
                history_ctx = "RIWAYAT PERCAKAPAN:\n" + "\n".join(lines) + "\n\n"

            prompt = (
                f"{history_ctx}"
                f"Konteks dari Tafsir Ath-Thabari:\n{context}\n"
                f"{user_constraints}\n"
                f"Pertanyaan: {req.query}\n\n"
                f"Jawaban (gunakan format terstruktur, sebut perawi eksplisit, "
                f"bedakan tarjih Ath-Thabari, patuhi semua constraint user):"
            )

            # Stream token-by-token from OpenRouter
            import requests as req_lib
            from app.core.config import settings
            resp = req_lib.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost:3000",
                    "X-Title": "Chatbot Tafsir Ath-Thabari",
                },
                json={
                    "model": settings.OPENROUTER_MODEL,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    "stream": True,
                    "temperature": 0.3,
                },
                stream=True,
                timeout=60,
            )
            resp.raise_for_status()

            for line in resp.iter_lines():
                if not line:
                    continue
                line = line.decode("utf-8")
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        token = chunk["choices"][0].get("delta", {}).get("content", "")
                        if token:
                            full_answer += token
                            yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
                    except Exception:
                        pass

        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        finally:
            if full_answer:
                session_svc.save_message(db, session.id, "assistant", full_answer, sources if 'sources' in dir() else [])
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
