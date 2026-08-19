from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class RatingCreateRequest(BaseModel):
    isbn10: str
    rating: int = Field(ge=1, le=5, description="Star rating between 1 and 5")
    review: Optional[str] = Field(None, max_length=1000, description="Optional textual review of the book")


class RatingResponse(BaseModel):
    rating_id: int
    roll_number: str
    isbn10: str
    rating: int
    review: Optional[str] = None
    created_at: Optional[datetime] = None
    book_average_rating: Optional[float] = None
    book_ratings_count: Optional[int] = None

    model_config = {"from_attributes": True}


class BookReviewItemResponse(BaseModel):
    rating_id: int
    roll_number: str
    user_name: str
    rating: int
    review: Optional[str] = None
    created_at: Optional[datetime] = None


class UserBookRatingResponse(BaseModel):
    isbn10: str
    rating: int
    review: Optional[str] = None
    created_at: Optional[datetime] = None
    book: BookResponseSummary | None = None


class BookResponseSummary(BaseModel):
    isbn10: str
    title: str
    authors: str | None = None
    thumbnail: str | None = None

    model_config = {"from_attributes": True}


UserBookRatingResponse.model_rebuild()
