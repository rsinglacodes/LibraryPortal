from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Optional
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status

from app.models.chat_history import ChatConversation, ChatMessageModel
from app.schemas.chat import (
    ChatMessageItemResponse,
    ChatSessionDetailResponse,
    ChatSessionMetaResponse,
    SuggestedBook,
)


def _generate_topic_title(user_query: str) -> str:
    """Generate a clean, concise conversation title from the first user query."""
    clean = re.sub(r"[^\w\s\-\'\"]", " ", user_query).strip()
    words = clean.split()
    if not words:
        return "Library Inquiry"

    # If it's a short query, capitalize appropriately
    if len(clean) <= 40:
        return clean.title()

    # Take first 5-8 words up to 45 chars
    truncated = " ".join(words[:6])
    if len(truncated) > 40:
        truncated = truncated[:38] + "..."
    else:
        truncated += "..."
    return truncated.title()


def list_user_conversations(db: Session, roll_number: str) -> list[ChatSessionMetaResponse]:
    stmt = (
        select(ChatConversation)
        .where(ChatConversation.roll_number == roll_number)
        .order_by(ChatConversation.updated_at.desc())
    )
    rows = db.scalars(stmt).all()
    return [
        ChatSessionMetaResponse(
            id=c.session_id,
            title=c.title,
            created_at=c.created_at.isoformat() if c.created_at else datetime.now().isoformat(),
            updated_at=c.updated_at.isoformat() if c.updated_at else datetime.now().isoformat(),
        )
        for c in rows
    ]


def get_conversation_detail(db: Session, roll_number: str, session_id: str) -> ChatSessionDetailResponse:
    conv = db.scalar(
        select(ChatConversation)
        .where(
            ChatConversation.roll_number == roll_number,
            ChatConversation.session_id == session_id,
        )
        .options(joinedload(ChatConversation.messages))
    )

    if not conv:
        # Check if messages exist for this session without a conversation record
        raw_msgs = db.scalars(
            select(ChatMessageModel)
            .where(ChatMessageModel.session_id == session_id)
            .order_by(ChatMessageModel.created_at.asc())
        ).all()
        formatted = []
        for m in raw_msgs:
            books_list = []
            if m.suggested_books_json:
                try:
                    books_list = json.loads(m.suggested_books_json)
                except Exception:
                    pass
            formatted.append(
                ChatMessageItemResponse(
                    id=m.id,
                    sender=m.role,
                    text=m.content,
                    emotion=m.emotion,
                    suggested_books=[SuggestedBook.model_validate(b) for b in books_list if isinstance(b, dict)],
                    created_at=m.created_at.isoformat() if m.created_at else None,
                )
            )
        return ChatSessionDetailResponse(
            session_id=session_id,
            title="Conversation",
            messages=formatted,
        )

    formatted_msgs = []
    for m in conv.messages:
        books_list = []
        if m.suggested_books_json:
            try:
                books_list = json.loads(m.suggested_books_json)
            except Exception:
                pass
        formatted_msgs.append(
            ChatMessageItemResponse(
                id=m.id,
                sender=m.role,
                text=m.content,
                emotion=m.emotion,
                suggested_books=[SuggestedBook.model_validate(b) for b in books_list if isinstance(b, dict)],
                created_at=m.created_at.isoformat() if m.created_at else None,
            )
        )

    return ChatSessionDetailResponse(
        session_id=conv.session_id,
        title=conv.title,
        messages=formatted_msgs,
    )


def save_chat_turn(
    db: Session,
    roll_number: str,
    session_id: str,
    user_text: str,
    assistant_text: str,
    emotion: Optional[str] = None,
    suggested_books: Optional[list[dict]] = None,
) -> ChatConversation:
    conv = db.scalar(
        select(ChatConversation).where(
            ChatConversation.roll_number == roll_number,
            ChatConversation.session_id == session_id,
        )
    )

    now = datetime.now()
    if not conv:
        # Create new conversation with auto-generated topic title
        topic_title = _generate_topic_title(user_text)
        conv = ChatConversation(
            roll_number=roll_number,
            session_id=session_id,
            title=topic_title,
            created_at=now,
            updated_at=now,
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)
    else:
        conv.updated_at = now

    # Save user message
    user_msg = ChatMessageModel(
        conversation_id=conv.id,
        session_id=session_id,
        role="user",
        content=user_text,
        created_at=now,
    )
    db.add(user_msg)

    # Save assistant response
    books_json_str = None
    if suggested_books:
        try:
            # clean dict representations for JSON storage
            clean_books = []
            for b in suggested_books:
                if isinstance(b, dict):
                    clean_books.append({
                        "isbn10": b.get("isbn10"),
                        "title": b.get("title", ""),
                        "authors": b.get("authors", "Unknown Author"),
                        "categories": b.get("categories", "General"),
                        "description": b.get("description", ""),
                        "thumbnail": b.get("thumbnail"),
                        "average_rating": b.get("average_rating"),
                        "total_copies": b.get("total_copies", 1),
                        "copies_available": b.get("copies_available", 1),
                        "is_available": b.get("is_available", True),
                    })
            books_json_str = json.dumps(clean_books)
        except Exception as e:
            print(f"Warning: could not serialize books to json: {e}")

    assistant_msg = ChatMessageModel(
        conversation_id=conv.id,
        session_id=session_id,
        role="assistant",
        content=assistant_text,
        emotion=emotion,
        suggested_books_json=books_json_str,
        created_at=now,
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(conv)
    return conv


def delete_conversation(db: Session, roll_number: str, session_id: str) -> dict:
    conv = db.scalar(
        select(ChatConversation).where(
            ChatConversation.roll_number == roll_number,
            ChatConversation.session_id == session_id,
        )
    )
    if conv:
        db.delete(conv)
        db.commit()
    else:
        # Delete any stray messages with this session_id
        db.query(ChatMessageModel).filter(ChatMessageModel.session_id == session_id).delete()
        db.commit()
    return {"status": "success", "session_id": session_id}


def update_conversation_title(db: Session, roll_number: str, session_id: str, new_title: str) -> ChatSessionMetaResponse:
    conv = db.scalar(
        select(ChatConversation).where(
            ChatConversation.roll_number == roll_number,
            ChatConversation.session_id == session_id,
        )
    )
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat conversation not found",
        )
    conv.title = new_title.strip()
    db.commit()
    db.refresh(conv)
    return ChatSessionMetaResponse(
        id=conv.session_id,
        title=conv.title,
        created_at=conv.created_at.isoformat(),
        updated_at=conv.updated_at.isoformat(),
    )
