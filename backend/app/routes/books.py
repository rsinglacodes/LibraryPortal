from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user_optional
from app.database.connection import get_db
from app.models import User, UserInteraction
from app.schemas.book import BookListResponse, BookResponse
from app.services import book_service

router = APIRouter(prefix="/books", tags=["books"])

@router.get("", response_model=BookListResponse)
def list_books(
    q: str | None = Query(None, description="Search term for title, author, description, or ISBN"),
    category: str | None = Query(None, description="Filter by category"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
) -> BookListResponse:
    # Log catalog search interaction
    if q and q.strip():
        try:
            roll = current_user.roll_number if current_user else "guest"
            interaction = UserInteraction(
                roll_number=roll,
                interaction_type="search",
                content=q.strip(),
            )
            db.add(interaction)
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"Warning: Could not log search interaction: {e}")

    return book_service.get_books(db, query=q, category=category, page=page, size=size)

@router.get("/categories", response_model=list[str])
def list_categories(db: Session = Depends(get_db)) -> list[str]:
    return book_service.get_unique_categories(db)

@router.get("/{isbn10}", response_model=BookResponse)
def get_book(
    isbn10: str,
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
) -> BookResponse:
    book = book_service.get_book_by_isbn(db, isbn10)
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found",
        )
    # Log view interaction
    try:
        roll = current_user.roll_number if current_user else "guest"
        interaction = UserInteraction(
            roll_number=roll,
            interaction_type="view",
            content=book.title,
            isbn10=book.isbn10,
        )
        db.add(interaction)
        db.commit()
    except Exception as e:
        db.rollback()

    return book_service._format_book_item(book, db)

