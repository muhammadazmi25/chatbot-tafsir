"""Session service — save/load chat history from MySQL."""

import json
import uuid
from typing import List, Dict, Optional
from sqlalchemy.orm import Session

from app.db.database import ChatSession, ChatMessage
from app.core.logging_config import get_logger

logger = get_logger('services.session')


def create_session(db: Session, title: str = None) -> ChatSession:
    session = ChatSession(
        session_uuid=str(uuid.uuid4()),
        title=title or "Percakapan Baru",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_session(db: Session, session_uuid: str) -> Optional[ChatSession]:
    return db.query(ChatSession).filter(
        ChatSession.session_uuid == session_uuid
    ).first()


def get_all_sessions(db: Session) -> List[ChatSession]:
    return db.query(ChatSession).order_by(ChatSession.updated_at.desc()).limit(50).all()


def save_message(
    db: Session,
    session_id: int,
    role: str,
    content: str,
    sources: List[Dict] = None,
) -> ChatMessage:
    msg = ChatMessage(
        session_id=session_id,
        role=role,
        content=content,
        sources=json.dumps(sources, ensure_ascii=False) if sources else None,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def get_session_messages(db: Session, session_id: int) -> List[ChatMessage]:
    return db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id
    ).order_by(ChatMessage.created_at.asc()).all()


def update_session_title(db: Session, session_id: int, title: str):
    db.query(ChatSession).filter(ChatSession.id == session_id).update({"title": title})
    db.commit()


def delete_session(db: Session, session_uuid: str):
    session = get_session(db, session_uuid)
    if session:
        db.delete(session)
        db.commit()
