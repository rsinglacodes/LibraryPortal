from __future__ import annotations

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_current_user
from app.database.connection import get_db
from app.models import Book, BorrowTransaction, Rating, User
from app.schemas.rating import (
    BookResponseSummary,
    BookReviewItemResponse,
    RatingCreateRequest,
    RatingResponse,
    UserBookRatingResponse,
)

router = APIRouter(prefix="/ratings", tags=["ratings"])


@router.post("", response_model=RatingResponse, status_code=status.HTTP_201_CREATED)
def add_or_update_rating(
    payload: RatingCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RatingResponse:
    clean_isbn = payload.isbn10.strip()
    book = db.get(Book, clean_isbn)
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found",
        )

    # 1. BORROW-ONLY RESTRICTION: Check if this user has ever borrowed this book
    has_borrowed = db.scalar(
        select(BorrowTransaction.id).where(
            BorrowTransaction.roll_number == current_user.roll_number,
            BorrowTransaction.isbn10 == clean_isbn,
        ).limit(1)
    )
    if not has_borrowed and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Rating restricted: You can only rate and review '{book.title}' after borrowing it from the library.",
        )

    # 2. Add or update rating & optional review
    stmt = select(Rating).where(
        Rating.roll_number == current_user.roll_number,
        Rating.isbn10 == clean_isbn,
    )
    existing = db.scalar(stmt)

    if existing:
        existing.rating = payload.rating
        if payload.review is not None:
            existing.review = payload.review.strip() if payload.review.strip() else None
        target_rating = existing
    else:
        new_rating = Rating(
            roll_number=current_user.roll_number,
            isbn10=clean_isbn,
            rating=payload.rating,
            review=payload.review.strip() if (payload.review and payload.review.strip()) else None,
            created_at=datetime.utcnow(),
        )
        db.add(new_rating)
        target_rating = new_rating

    db.commit()
    db.refresh(target_rating)

    # 3. DYNAMIC AVERAGE RATING RECALCULATION & PERSISTENCE
    stats = db.execute(
        select(func.avg(Rating.rating), func.count(Rating.rating_id)).where(
            Rating.isbn10 == clean_isbn
        )
    ).first()

    if stats:
        avg_val, cnt_val = stats
        if avg_val is not None:
            book.average_rating = min(5.0, max(1.0, round(float(avg_val), 2)))
        else:
            book.average_rating = min(5.0, max(1.0, float(payload.rating)))
        book.ratings_count = int(cnt_val) if cnt_val is not None else 1
        db.commit()
        db.refresh(book)

    return RatingResponse(
        rating_id=target_rating.rating_id,
        roll_number=target_rating.roll_number,
        isbn10=target_rating.isbn10,
        rating=target_rating.rating,
        review=target_rating.review,
        created_at=target_rating.created_at,
        book_average_rating=book.average_rating,
        book_ratings_count=book.ratings_count,
    )


@router.get("/book/{isbn10}", response_model=list[BookReviewItemResponse])
def get_book_reviews(
    isbn10: str,
    limit: int = 2,
    db: Session = Depends(get_db),
) -> list[BookReviewItemResponse]:
    clean_isbn = isbn10.strip()
    stmt = (
        select(Rating)
        .options(joinedload(Rating.user))
        .where(Rating.isbn10 == clean_isbn)
        .order_by(Rating.created_at.desc().nullslast(), Rating.rating_id.desc())
        .limit(max(1, min(limit, 50)))
    )
    ratings = db.scalars(stmt).all()

    results = []
    for r in ratings:
        user_name = r.user.name if r.user else f"Student {r.roll_number}"
        results.append(
            BookReviewItemResponse(
                rating_id=r.rating_id,
                roll_number=r.roll_number,
                user_name=user_name,
                rating=r.rating,
                review=r.review,
                created_at=r.created_at,
            )
        )
    return results


@router.get("/me", response_model=list[UserBookRatingResponse])
def get_my_ratings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[UserBookRatingResponse]:
    stmt = (
        select(Rating)
        .where(Rating.roll_number == current_user.roll_number)
        .order_by(Rating.created_at.desc().nullslast(), Rating.rating.desc())
    )
    ratings = db.scalars(stmt).all()

    result = []
    for r in ratings:
        book_summary = None
        if r.book:
            book_summary = BookResponseSummary.model_validate(r.book)
        result.append(
            UserBookRatingResponse(
                isbn10=r.isbn10,
                rating=r.rating,
                review=r.review,
                created_at=r.created_at,
                book=book_summary,
            )
        )
    return result
