from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Any, Optional

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    session_id: str = "default"

class SuggestedBook(BaseModel):
    isbn10: Optional[str] = None
    title: str
    authors: Optional[str] = "Unknown Author"
    categories: Optional[str] = "General"
    description: Optional[str] = ""
    thumbnail: Optional[str] = None
    average_rating: Optional[float] = None
    total_copies: Optional[int] = 1
    copies_available: Optional[int] = 1
    is_available: Optional[bool] = True

class ChatResponse(BaseModel):
    response: str
    emotion: str
    suggested_books: list[SuggestedBook] = []

class ResetSessionResponse(BaseModel):
    status: str
    session_id: str
    message: str


class ChatSessionMetaResponse(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str


class ChatMessageItemResponse(BaseModel):
    id: Optional[int] = None
    sender: str  # 'user' | 'assistant'
    text: str
    emotion: Optional[str] = None
    suggested_books: list[SuggestedBook] = []
    created_at: Optional[str] = None


class ChatSessionDetailResponse(BaseModel):
    session_id: str
    title: str
    messages: list[ChatMessageItemResponse]


class UpdateSessionTitleRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)

