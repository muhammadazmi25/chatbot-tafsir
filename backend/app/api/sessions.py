"""Sessions API — GET /api/v1/sessions"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import json

from app.db.database import get_db
from app.core.logging_config import get_logger
import app.services.session_service as session_svc

logger = get_logger('api.sessions')
router = APIRouter()


@router.get("")
def list_sessions(db: Session = Depends(get_db)):
    sessions = session_svc.get_all_sessions(db)
    return [
        {
            "id": s.id,
            "session_uuid": s.session_uuid,
            "title": s.title,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        }
        for s in sessions
    ]


@router.get("/{session_uuid}/messages")
def get_messages(session_uuid: str, db: Session = Depends(get_db)):
    session = session_svc.get_session(db, session_uuid)
    if not session:
        raise HTTPException(404, "Session not found")
    messages = session_svc.get_session_messages(db, session.id)
    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "sources": json.loads(m.sources) if m.sources else [],
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in messages
    ]


@router.delete("/{session_uuid}")
def delete_session(session_uuid: str, db: Session = Depends(get_db)):
    session = session_svc.get_session(db, session_uuid)
    if not session:
        raise HTTPException(404, "Session not found")
    session_svc.delete_session(db, session_uuid)
    return {"ok": True}
