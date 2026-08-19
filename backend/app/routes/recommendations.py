from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_current_user_optional
from app.database.connection import get_db
from app.ml.recommendation import recommendation_engine
from app.models import User, UserInteraction, Rating
from app.schemas.book import BookResponse

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


class TrackInteractionRequest(BaseModel):
    interaction_type: str  # 'search', 'chat', 'view', 'explore'
    content: str | None = None
    isbn10: str | None = None
    roll_number: str | None = None


class UserSignalsResponse(BaseModel):
    roll_number: str
    total_ratings: int
    total_explored: int
    total_searches: int
    total_chats: int
    active_profile: bool


@router.get("", response_model=list[BookResponse])
def get_recommendations(
    limit: int = Query(12, ge=1, le=50, description="Number of recommendations to return"),
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
) -> list[BookResponse]:
    roll_num = current_user.roll_number if current_user else "guest"
    return recommendation_engine.recommend_for_user(
        db=db,
        roll_number=roll_num,
        top_n=limit,
    )


@router.post("/track", status_code=status.HTTP_200_OK)
def track_interaction(
    payload: TrackInteractionRequest,
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    roll_num = current_user.roll_number if current_user else (payload.roll_number or "guest")
    try:
        interaction = UserInteraction(
            roll_number=roll_num,
            interaction_type=payload.interaction_type,
            content=payload.content,
            isbn10=payload.isbn10,
        )
        db.add(interaction)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Warning: Could not record interaction: {e}")
    return {"status": "success", "tracked": payload.interaction_type, "roll_number": roll_num}


@router.get("/signals", response_model=UserSignalsResponse)
def get_user_signals(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserSignalsResponse:
    roll = current_user.roll_number
    ratings_cnt = db.scalar(select(func.count()).where(Rating.roll_number == roll)) or 0
    explored_cnt = db.scalar(
        select(func.count()).where(
            UserInteraction.roll_number == roll,
            UserInteraction.interaction_type.in_(["view", "explore"]),
        )
    ) or 0
    searches_cnt = db.scalar(
        select(func.count()).where(
            UserInteraction.roll_number == roll,
            UserInteraction.interaction_type == "search",
        )
    ) or 0
    chats_cnt = db.scalar(
        select(func.count()).where(
            UserInteraction.roll_number == roll,
            UserInteraction.interaction_type == "chat",
        )
    ) or 0

    return UserSignalsResponse(
        roll_number=roll,
        total_ratings=ratings_cnt,
        total_explored=explored_cnt,
        total_searches=searches_cnt,
        total_chats=chats_cnt,
        active_profile=(ratings_cnt + explored_cnt + searches_cnt + chats_cnt) > 0,
    )
