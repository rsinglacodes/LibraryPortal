from __future__ import annotations

from pydantic import BaseModel, Field

class BookResponse(BaseModel):
    isbn10: str
    isbn13: str | None = None
    title: str
    subtitle: str | None = None
    authors: str | None = None
    categories: str | None = None
    description: str | None = None
    thumbnail: str | None = None
    publisher: str | None = None
    published_year: int | None = None
    num_pages: int | None = None
    average_rating: float | None = None
    ratings_count: int | None = None

    total_copies: int | None = None
    copies_available: int | None = None
    is_available: bool | None = None
    expected_return_date: str | None = None

    model_config = {"from_attributes": True}

class BookListResponse(BaseModel):
    items: list[BookResponse]
    total: int
    page: int
    size: int
    pages: int
