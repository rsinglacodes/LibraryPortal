from __future__ import annotations

import json
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_current_user_optional
from app.database.connection import get_db, get_session_local
from app.ml.llm_assistant import llm_assistant, session_store
from app.models import User, UserInteraction
from app.schemas.chat import (
    ChatMessageItemResponse,
    ChatRequest,
    ChatResponse,
    ChatSessionDetailResponse,
    ChatSessionMetaResponse,
    ResetSessionResponse,
    UpdateSessionTitleRequest,
)
from app.services import chat_history_service

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/stream")
def stream_chat_with_assistant(
    payload: ChatRequest,
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    roll_num = current_user.roll_number if current_user else "guest"
    user_msg = payload.message
    sess_id = payload.session_id

    def event_generator():
        # Dedicated session for streaming background persistence
        SessionLocal = get_session_local()
        stream_db = SessionLocal()
        try:
            full_text = ""
            final_emotion = "neutral"
            final_suggested = []

            for sse_event in llm_assistant.stream_chat(
                db=stream_db,
                user_query=user_msg,
                session_id=sess_id,
            ):
                yield sse_event
                # Parse event data for background saving
                if sse_event.startswith("data: "):
                    try:
                        raw = json.loads(sse_event[6:].strip())
                        if raw.get("type") == "done":
                            final_emotion = raw.get("emotion", "neutral")
                            final_suggested = raw.get("suggested_books", [])
                            full_text = raw.get("full_text", "")
                    except Exception:
                        pass

            # Save chat turn if logged in
            if current_user and full_text:
                try:
                    chat_history_service.save_chat_turn(
                        db=stream_db,
                        roll_number=roll_num,
                        session_id=sess_id,
                        user_text=user_msg,
                        assistant_text=full_text,
                        emotion=final_emotion,
                        suggested_books=final_suggested,
                    )
                except Exception as e:
                    print(f"Streaming save_chat_turn error: {e}")

            # Save interaction
            try:
                primary_isbn = final_suggested[0].get("isbn10") if (final_suggested and isinstance(final_suggested[0], dict)) else None
                interaction = UserInteraction(
                    roll_number=roll_num,
                    interaction_type="chat",
                    content=user_msg,
                    isbn10=primary_isbn,
                )
                stream_db.add(interaction)
                stream_db.commit()
            except Exception as e:
                stream_db.rollback()
                print(f"Streaming interaction log error: {e}")
        finally:
            stream_db.close()

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("", response_model=ChatResponse)
def chat_with_assistant(
    payload: ChatRequest,
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
) -> ChatResponse:
    try:
        res = llm_assistant.process_chat(
            db=db,
            user_query=payload.message,
            session_id=payload.session_id,
        )

        roll_num = current_user.roll_number if current_user else "guest"
        suggested = res.get("suggested_books", [])

        # Persist conversation and messages directly into PostgreSQL
        if current_user:
            try:
                chat_history_service.save_chat_turn(
                    db=db,
                    roll_number=current_user.roll_number,
                    session_id=payload.session_id,
                    user_text=payload.message,
                    assistant_text=res.get("response", ""),
                    emotion=res.get("emotion"),
                    suggested_books=suggested,
                )
            except Exception as e:
                print(f"Warning: could not save persistent chat turn: {e}")

        # Log chat query & suggested books into user interaction profile
        try:
            primary_isbn = suggested[0].get("isbn10") if (suggested and isinstance(suggested[0], dict)) else None
            interaction = UserInteraction(
                roll_number=roll_num,
                interaction_type="chat",
                content=payload.message,
                isbn10=primary_isbn,
            )
            db.add(interaction)
            if suggested and len(suggested) > 1:
                for b in suggested[1:]:
                    if isinstance(b, dict) and b.get("isbn10"):
                        db.add(UserInteraction(
                            roll_number=roll_num,
                            interaction_type="chat_suggested",
                            content=payload.message,
                            isbn10=b.get("isbn10")
                        ))
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"Warning: Could not log chat interaction: {e}")

        return ChatResponse.model_validate(res)
    except Exception as e:
        print(f"Chat route error: {e}")
        return ChatResponse(
            response="I'm here to help! Our library catalog is ready. What genre or title would you like to explore?",
            emotion="neutral",
            suggested_books=[],
        )


@router.get("/sessions", response_model=list[ChatSessionMetaResponse])
def get_user_chat_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ChatSessionMetaResponse]:
    return chat_history_service.list_user_conversations(db, current_user.roll_number)


@router.get("/sessions/{session_id}", response_model=ChatSessionDetailResponse)
def get_session_messages(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatSessionDetailResponse:
    return chat_history_service.get_conversation_detail(db, current_user.roll_number, session_id)


@router.delete("/sessions/{session_id}")
def delete_chat_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session_store.reset_session(session_id)
    return chat_history_service.delete_conversation(db, current_user.roll_number, session_id)


@router.put("/sessions/{session_id}/title", response_model=ChatSessionMetaResponse)
def update_chat_session_title(
    session_id: str,
    payload: UpdateSessionTitleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatSessionMetaResponse:
    return chat_history_service.update_conversation_title(
        db, current_user.roll_number, session_id, payload.title
    )


@router.post("/reset", response_model=ResetSessionResponse)
def reset_chat_session(payload: dict) -> ResetSessionResponse:
    session_id = payload.get("session_id", "default")
    session_store.reset_session(session_id)
    return ResetSessionResponse(
        status="success",
        session_id=session_id,
        message="Session memory cleared successfully",
    )

