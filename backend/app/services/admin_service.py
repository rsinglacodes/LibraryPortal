from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy import func, or_, select, and_, desc, asc
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status

from app.core.inventory import get_simulated_availability
from app.models.book import Book
from app.models.borrow import BorrowTransaction
from app.models.interaction import UserInteraction
from app.models.rating import Rating
from app.models.user import User
from app.schemas.admin import (
    AdminOverviewResponse,
    BookDemandItem,
    BorrowRecordResponse,
    CreateBookRequest,
    DamageSummaryResponse,
    DemandAnalyticsResponse,
    ImposeFineRequest,
    IssueBookRequest,
    PayFineRequest,
    UpdateBookRequest,
    UserFineSummaryResponse,
    UserLoanItem,
    WaiveFineRequest,
)



def _get_now() -> datetime:
    return datetime.now()


def _compute_and_sync_overdue(tx: BorrowTransaction, now: datetime | None = None) -> float:
    """
    Computes fine dynamically based on issue and due dates:
    If overdue (now > due_date): fine is ₹10 base fee + ₹10 per overdue day.
    """
    if now is None:
        now = _get_now()

    effective_time = tx.returned_at if tx.returned_at else (now if tx.status != "returned" else None)
    if effective_time and tx.due_date and effective_time > tx.due_date:
        overdue_days = max(1, (effective_time - tx.due_date).days)
        calculated_fine = round(10.0 + (overdue_days * 10.0), 2)

        if (tx.fine_amount or 0.0) < calculated_fine:
            tx.fine_amount = calculated_fine
            tx.fine_reason = f"Overdue fine: ₹10 base + ₹10/day ({overdue_days} day{'s' if overdue_days > 1 else ''} late)"
            if tx.fine_status in ("none", None):
                tx.fine_status = "imposed"
        return calculated_fine
    return tx.fine_amount or 0.0


def _format_borrow_record(tx: BorrowTransaction) -> BorrowRecordResponse:
    now = _get_now()
    _compute_and_sync_overdue(tx, now)

    cur_status = tx.status
    if cur_status == "active" and tx.due_date and tx.due_date < now:
        cur_status = "overdue"

    fine_rem = max(0.0, (tx.fine_amount or 0.0) - (tx.fine_paid or 0.0) - (tx.fine_waived or 0.0))

    return BorrowRecordResponse(
        id=tx.id,
        roll_number=tx.roll_number,
        user_name=tx.user.name if tx.user else tx.roll_number,
        user_email=tx.user.email if tx.user else "",
        isbn10=tx.isbn10,
        book_title=tx.book.title if tx.book else "Unknown Book",
        book_authors=tx.book.authors if tx.book else None,
        book_thumbnail=tx.book.thumbnail if tx.book else None,
        borrowed_at=tx.borrowed_at,
        due_date=tx.due_date,
        returned_at=tx.returned_at,
        status=cur_status,
        fine_amount=float(tx.fine_amount or 0.0),
        fine_paid=float(tx.fine_paid or 0.0),
        fine_waived=float(tx.fine_waived or 0.0),
        fine_remaining=round(fine_rem, 2),
        fine_reason=tx.fine_reason,
        fine_status=tx.fine_status,
        damage_detected=bool(tx.damage_detected) if tx.damage_detected is not None else False,
        damage_types=tx.damage_types,
    )



def get_admin_overview(db: Session) -> AdminOverviewResponse:
    total_users = db.scalar(select(func.count()).where(User.roll_number != "admin")) or 0
    total_books = db.scalar(select(func.count(Book.isbn10))) or 0

    now = _get_now()
    active_borrows = db.scalar(
        select(func.count(BorrowTransaction.id)).where(BorrowTransaction.status == "active")
    ) or 0

    overdue_borrows = db.scalar(
        select(func.count(BorrowTransaction.id)).where(
            BorrowTransaction.status == "active",
            BorrowTransaction.due_date < now,
        )
    ) or 0

    fine_sums = db.execute(
        select(
            func.coalesce(func.sum(BorrowTransaction.fine_amount), 0.0),
            func.coalesce(func.sum(BorrowTransaction.fine_paid), 0.0),
            func.coalesce(func.sum(BorrowTransaction.fine_waived), 0.0),
        )
    ).one()

    tot_imposed = float(fine_sums[0])
    tot_paid = float(fine_sums[1])
    tot_waived = float(fine_sums[2])
    tot_remaining = max(0.0, tot_imposed - tot_paid - tot_waived)

    return AdminOverviewResponse(
        total_users=total_users,
        total_books=total_books,
        active_borrows=active_borrows,
        overdue_borrows=overdue_borrows,
        total_fines_imposed=round(tot_imposed, 2),
        total_fines_paid=round(tot_paid, 2),
        total_fines_waived=round(tot_waived, 2),
        total_fines_remaining=round(tot_remaining, 2),
    )


def list_borrows(
    db: Session,
    status_filter: Optional[str] = None,
    q: Optional[str] = None,
) -> list[BorrowRecordResponse]:
    stmt = (
        select(BorrowTransaction)
        .options(joinedload(BorrowTransaction.user), joinedload(BorrowTransaction.book))
        .order_by(BorrowTransaction.borrowed_at.desc())
    )

    now = _get_now()
    if status_filter == "active":
        stmt = stmt.where(BorrowTransaction.status == "active", BorrowTransaction.due_date >= now)
    elif status_filter == "overdue":
        stmt = stmt.where(BorrowTransaction.status == "active", BorrowTransaction.due_date < now)
    elif status_filter == "returned":
        stmt = stmt.where(BorrowTransaction.status == "returned")
    elif status_filter == "fines":
        stmt = stmt.where((BorrowTransaction.fine_amount - BorrowTransaction.fine_paid - BorrowTransaction.fine_waived) > 0)

    records = db.scalars(stmt).all()

    # In-memory query search if provided
    if q and q.strip():
        q_clean = q.strip().lower()
        records = [
            r for r in records
            if (q_clean in r.roll_number.lower())
            or (r.user and q_clean in r.user.name.lower())
            or (q_clean in r.isbn10.lower())
            or (r.book and q_clean in r.book.title.lower())
        ]

    return [_format_borrow_record(r) for r in records]


def issue_book(db: Session, payload: IssueBookRequest) -> BorrowRecordResponse:
    user = db.get(User, payload.roll_number.strip())
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with roll number '{payload.roll_number}' not found",
        )

    book = db.get(Book, payload.isbn10.strip())
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book with ISBN '{payload.isbn10}' not found",
        )

    # Check if user already has an active borrow of this book
    existing_active = db.scalar(
        select(BorrowTransaction).where(
            BorrowTransaction.roll_number == payload.roll_number.strip(),
            BorrowTransaction.isbn10 == payload.isbn10.strip(),
            BorrowTransaction.status == "active",
        )
    )
    if existing_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Student already has an active loan for this book",
        )

    # Check real-time dynamic available copies
    active_loans = db.scalar(
        select(func.count(BorrowTransaction.id)).where(
            BorrowTransaction.isbn10 == payload.isbn10.strip(),
            BorrowTransaction.status == "active",
        )
    ) or 0
    tot_copies = book.total_copies if (book.total_copies is not None) else 5
    available_copies = max(0, tot_copies - active_loans)

    if available_copies <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot issue '{book.title}': All {tot_copies} copies are currently checked out (0 copies available in stock).",
        )

    now = _get_now()
    due = now + timedelta(days=payload.days or 14)


    tx = BorrowTransaction(
        roll_number=payload.roll_number.strip(),
        isbn10=payload.isbn10.strip(),
        borrowed_at=now,
        due_date=due,
        status="active",
        fine_amount=0.0,
        fine_paid=0.0,
        fine_waived=0.0,
        fine_status="none",
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    # Track interaction for recommendation signals
    try:
        db.add(UserInteraction(
            roll_number=payload.roll_number.strip(),
            interaction_type="borrow",
            content=f"Borrowed {book.title}",
            isbn10=book.isbn10,
        ))
        db.commit()
    except Exception:
        db.rollback()

    return _format_borrow_record(tx)


def return_book(db: Session, borrow_id: int) -> BorrowRecordResponse:
    tx = db.get(BorrowTransaction, borrow_id)
    if not tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Borrow transaction ID {borrow_id} not found",
        )

    if tx.status == "returned":
        return _format_borrow_record(tx)

    now = _get_now()
    tx.returned_at = now
    tx.status = "returned"

    # Calculate automatic overdue fine if past due
    if tx.due_date and now > tx.due_date:
        overdue_days = max(1, (now - tx.due_date).days)
        late_fee = round(10.0 + (overdue_days * 10.0), 2)  # ₹10 base + ₹10 per overdue day
        if (tx.fine_amount or 0.0) < late_fee:
            tx.fine_amount = late_fee
            tx.fine_reason = f"Overdue fine: ₹10 base + ₹10/day ({overdue_days} day{'s' if overdue_days > 1 else ''} late)"
            if tx.fine_status in ("none", None):
                tx.fine_status = "imposed"

    db.commit()
    db.refresh(tx)
    return _format_borrow_record(tx)



def impose_fine(db: Session, payload: ImposeFineRequest) -> BorrowRecordResponse:
    user = db.get(User, payload.roll_number.strip())
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with roll number '{payload.roll_number}' not found",
        )

    tx = None
    if payload.borrow_id:
        tx = db.get(BorrowTransaction, payload.borrow_id)

    if not tx:
        # Find latest active or recent borrow for this user
        tx = db.scalar(
            select(BorrowTransaction)
            .where(BorrowTransaction.roll_number == payload.roll_number.strip())
            .order_by(BorrowTransaction.borrowed_at.desc())
        )

    if not tx:
        # If no borrow transaction exists at all, find any available book to attach record or create dedicated fine transaction
        first_book = db.scalar(select(Book).limit(1))
        isbn = first_book.isbn10 if first_book else "0000000000"
        now = _get_now()
        tx = BorrowTransaction(
            roll_number=payload.roll_number.strip(),
            isbn10=isbn,
            borrowed_at=now,
            due_date=now,
            returned_at=now,
            status="returned",
            fine_amount=payload.amount,
            fine_paid=0.0,
            fine_waived=0.0,
            fine_reason=payload.reason,
            fine_status="imposed",
        )
        db.add(tx)
    else:
        tx.fine_amount = (tx.fine_amount or 0.0) + payload.amount
        tx.fine_reason = payload.reason
        tx.fine_status = "imposed"

    db.commit()
    db.refresh(tx)
    return _format_borrow_record(tx)


def waive_fine(db: Session, payload: WaiveFineRequest) -> list[BorrowRecordResponse]:
    updated_records = []

    if payload.borrow_id:
        tx = db.get(BorrowTransaction, payload.borrow_id)
        if not tx:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Borrow transaction ID {payload.borrow_id} not found",
            )
        rem = tx.fine_remaining
        if rem > 0:
            waive_amt = payload.amount if (payload.amount and payload.amount < rem) else rem
            tx.fine_waived = (tx.fine_waived or 0.0) + waive_amt
            if tx.fine_remaining <= 0:
                tx.fine_status = "waived"
            else:
                tx.fine_status = "partial"
            if payload.reason:
                tx.fine_reason = f"{tx.fine_reason or ''} (Waived: {payload.reason})".strip()
            db.commit()
            db.refresh(tx)
        updated_records.append(_format_borrow_record(tx))
        return updated_records

    if payload.roll_number:
        stmt = select(BorrowTransaction).where(BorrowTransaction.roll_number == payload.roll_number.strip())
        user_borrows = db.scalars(stmt).all()
        rem_to_waive = payload.amount if payload.amount is not None else float("inf")

        for tx in user_borrows:
            tx_rem = tx.fine_remaining
            if tx_rem > 0 and rem_to_waive > 0:
                cur_waive = min(tx_rem, rem_to_waive)
                tx.fine_waived = (tx.fine_waived or 0.0) + cur_waive
                rem_to_waive -= cur_waive
                if tx.fine_remaining <= 0:
                    tx.fine_status = "waived"
                else:
                    tx.fine_status = "partial"
                if payload.reason:
                    tx.fine_reason = f"{tx.fine_reason or ''} (Waived: {payload.reason})".strip()
                updated_records.append(_format_borrow_record(tx))

        db.commit()
        return updated_records

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Provide borrow_id or roll_number to remove/waive fine",
    )


def pay_fine(db: Session, payload: PayFineRequest) -> list[BorrowRecordResponse]:
    updated_records = []

    if payload.borrow_id:
        tx = db.get(BorrowTransaction, payload.borrow_id)
        if not tx:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Borrow transaction ID {payload.borrow_id} not found",
            )
        rem = tx.fine_remaining
        pay_amt = min(rem, payload.amount)
        tx.fine_paid = (tx.fine_paid or 0.0) + pay_amt
        if tx.fine_remaining <= 0:
            tx.fine_status = "paid"
        else:
            tx.fine_status = "partial"
        db.commit()
        db.refresh(tx)
        updated_records.append(_format_borrow_record(tx))
        return updated_records

    if payload.roll_number:
        stmt = select(BorrowTransaction).where(BorrowTransaction.roll_number == payload.roll_number.strip())
        user_borrows = db.scalars(stmt).all()
        rem_to_pay = payload.amount

        for tx in user_borrows:
            tx_rem = tx.fine_remaining
            if tx_rem > 0 and rem_to_pay > 0:
                cur_pay = min(tx_rem, rem_to_pay)
                tx.fine_paid = (tx.fine_paid or 0.0) + cur_pay
                rem_to_pay -= cur_pay
                if tx.fine_remaining <= 0:
                    tx.fine_status = "paid"
                else:
                    tx.fine_status = "partial"
                updated_records.append(_format_borrow_record(tx))

        db.commit()
        return updated_records

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Provide borrow_id or roll_number for fine payment",
    )


def get_fines_summary(db: Session) -> list[UserFineSummaryResponse]:
    users = db.scalars(
        select(User).where(User.roll_number != "admin").order_by(User.name.asc())
    ).all()

    results: list[UserFineSummaryResponse] = []
    for u in users:
        borrows = u.borrows or []
        tot_borrows = len(borrows)
        active_cnt = sum(1 for b in borrows if b.status == "active")

        tot_imposed = sum((b.fine_amount or 0.0) for b in borrows)
        tot_paid = sum((b.fine_paid or 0.0) for b in borrows)
        tot_waived = sum((b.fine_waived or 0.0) for b in borrows)
        tot_remaining = max(0.0, tot_imposed - tot_paid - tot_waived)

        # Build detailed loan records for this user
        loan_items: list[UserLoanItem] = []
        for b in borrows:
            fine_rem = max(0.0, (b.fine_amount or 0.0) - (b.fine_paid or 0.0) - (b.fine_waived or 0.0))
            loan_items.append(
                UserLoanItem(
                    borrow_id=b.id,
                    isbn10=b.isbn10,
                    book_title=b.book.title if b.book else "Unknown Book",
                    book_authors=b.book.authors if b.book else None,
                    book_thumbnail=b.book.thumbnail if b.book else None,
                    quantity=1,
                    borrowed_at=b.borrowed_at,
                    due_date=b.due_date,
                    returned_at=b.returned_at,
                    status=b.status,
                    fine_amount=float(b.fine_amount or 0.0),
                    fine_paid=float(b.fine_paid or 0.0),
                    fine_waived=float(b.fine_waived or 0.0),
                    fine_remaining=round(fine_rem, 2),
                    fine_reason=b.fine_reason,
                )
            )

        results.append(
            UserFineSummaryResponse(
                roll_number=u.roll_number,
                name=u.name,
                email=u.email,
                active_borrows_count=active_cnt,
                total_borrows_count=tot_borrows,
                total_fines_imposed=round(tot_imposed, 2),
                total_fines_paid=round(tot_paid, 2),
                total_fines_waived=round(tot_waived, 2),
                total_fines_remaining=round(tot_remaining, 2),
                loans=loan_items,
            )
        )

    # Sort users with highest remaining fines or most active loans at top
    results.sort(key=lambda x: (x.total_fines_remaining, x.active_borrows_count, x.total_borrows_count), reverse=True)
    return results


def get_demand_analytics(db: Session) -> DemandAnalyticsResponse:
    """
    Computes top 10 most demanding and top 10 least demanding books for the librarian to restock.
    Combines borrow count (5x), search & views (2x), rating volume (1.5x),
    and UNMET DEMAND for unavailable books (8x extra weight if user showed interest when out of stock).
    """
    # 1. Borrow counts per book
    borrow_counts_raw = db.execute(
        select(BorrowTransaction.isbn10, func.count(BorrowTransaction.id))
        .group_by(BorrowTransaction.isbn10)
    ).all()
    borrow_map = {isbn: cnt for isbn, cnt in borrow_counts_raw}

    # 2. Search & View interactions per book
    interaction_counts_raw = db.execute(
        select(UserInteraction.isbn10, func.count(UserInteraction.id))
        .where(UserInteraction.isbn10.is_not(None))
        .group_by(UserInteraction.isbn10)
    ).all()
    interaction_map = {isbn: cnt for isbn, cnt in interaction_counts_raw}

    # 3. Active borrow count per book to get exact live copies
    active_borrows_raw = db.execute(
        select(BorrowTransaction.isbn10, func.count(BorrowTransaction.id))
        .where(BorrowTransaction.status == "active")
        .group_by(BorrowTransaction.isbn10)
    ).all()
    active_borrows_map = {isbn: cnt for isbn, cnt in active_borrows_raw}

    # 4. Unmet demand interactions (specifically tracked when book is unavailable or copies = 0)
    unmet_counts_raw = db.execute(
        select(UserInteraction.isbn10, func.count(UserInteraction.id))
        .where(
            UserInteraction.isbn10.is_not(None),
            UserInteraction.interaction_type.in_(["unavailable_interest", "borrow_attempt_unavailable", "out_of_stock_view"]),
        )
        .group_by(UserInteraction.isbn10)
    ).all()
    unmet_map = {isbn: cnt for isbn, cnt in unmet_counts_raw}

    all_books = db.scalars(select(Book)).all()

    evaluated_books: list[BookDemandItem] = []

    for b in all_books:
        b_borrows = borrow_map.get(b.isbn10, 0)
        b_interactions = interaction_map.get(b.isbn10, 0)
        tot_copies = b.total_copies or 5
        active_loans = active_borrows_map.get(b.isbn10, 0)
        avail_copies = max(0, tot_copies - active_loans)

        avg_rating = b.average_rating or 3.0
        ratings_cnt = b.ratings_count or 0

        # Unmet demand: explicitly tracked interest when unavailable PLUS interest on 0-stock books
        unmet_cnt = unmet_map.get(b.isbn10, 0)
        if avail_copies == 0 and b_interactions > 0:
            unmet_cnt = max(unmet_cnt, b_interactions)

        # Weighted Demand Score:
        # borrows (5x) + general searches (2x) + unmet unavailable interest (8x) + ratings
        score = (
            (b_borrows * 5.0)
            + (b_interactions * 2.0)
            + (unmet_cnt * 8.0)
            + (ratings_cnt * 0.05)
            + (avg_rating * 1.0)
        )

        # Restock Recommendation Status
        if avail_copies == 0:
            restock_status = "URGENT_RESTOCK"
            reorder_qty = max(5, b_borrows + unmet_cnt + 3)
        elif avail_copies <= 2 and (score >= 5.0 or unmet_cnt > 0):
            restock_status = "LOW_STOCK"
            reorder_qty = max(3, math.ceil(tot_copies * 0.5) + unmet_cnt)
        elif score > 15.0 and avail_copies <= 3:
            restock_status = "URGENT_RESTOCK"
            reorder_qty = 5
        elif b_borrows == 0 and b_interactions == 0 and ratings_cnt == 0:
            restock_status = "LOW_DEMAND"
            reorder_qty = 0
        elif avail_copies >= tot_copies and b_borrows == 0:
            restock_status = "OVERSTOCKED"
            reorder_qty = 0
        else:
            restock_status = "OPTIMAL"
            reorder_qty = 0

        evaluated_books.append(
            BookDemandItem(
                isbn10=b.isbn10,
                title=b.title,
                authors=b.authors,
                categories=b.categories,
                thumbnail=b.thumbnail,
                average_rating=float(b.average_rating) if b.average_rating is not None else None,
                ratings_count=b.ratings_count,
                total_copies=tot_copies,
                copies_available=avail_copies,
                borrow_count=b_borrows,
                search_interaction_count=b_interactions,
                unmet_demand_count=unmet_cnt,
                demand_score=round(score, 2),
                restock_status=restock_status,
                recommended_restock_qty=reorder_qty,
            )
        )

    # Sort descending for top demanding
    evaluated_books.sort(
        key=lambda x: (x.demand_score, x.unmet_demand_count, x.borrow_count, x.average_rating or 0),
        reverse=True,
    )
    top_10 = evaluated_books[:10]

    # Sort ascending for least demanding
    least_sorted = sorted(
        evaluated_books,
        key=lambda x: (x.demand_score, x.borrow_count, x.search_interaction_count),
    )
    least_10 = least_sorted[:10]

    return DemandAnalyticsResponse(
        top_demanding=top_10,
        least_demanding=least_10,
    )



def create_book(db: Session, payload: CreateBookRequest) -> Book:
    isbn_clean = payload.isbn10.strip()
    existing = db.get(Book, isbn_clean)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Book with ISBN '{isbn_clean}' already exists",
        )

    book = Book(
        isbn10=isbn_clean,
        isbn13=payload.isbn13.strip() if payload.isbn13 else None,
        title=payload.title.strip(),
        subtitle=payload.subtitle.strip() if payload.subtitle else None,
        authors=payload.authors.strip() if payload.authors else "Unknown Author",
        categories=payload.categories.strip() if payload.categories else "General",
        description=payload.description.strip() if payload.description else "",
        thumbnail=payload.thumbnail.strip() if payload.thumbnail else None,
        publisher=payload.publisher.strip() if payload.publisher else None,
        published_year=payload.published_year,
        num_pages=payload.num_pages,
        total_copies=payload.total_copies or 5,
        average_rating=None,
        ratings_count=0,
    )
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


def update_book(db: Session, isbn10: str, payload: UpdateBookRequest) -> Book:
    book = db.get(Book, isbn10.strip())
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book with ISBN '{isbn10}' not found",
        )

    for field, val in payload.model_dump(exclude_unset=True).items():
        if val is not None:
            setattr(book, field, val)

    db.commit()
    db.refresh(book)
    return book


def delete_book(db: Session, isbn10: str) -> dict:
    book = db.get(Book, isbn10.strip())
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book with ISBN '{isbn10}' not found",
        )

    db.delete(book)
    db.commit()
    return {"status": "success", "deleted_isbn10": isbn10}


# ── Damage-detection admin helpers ────────────────────────────────────────────────

def get_damaged_returns(db: Session) -> list[BorrowRecordResponse]:
    """
    Return all borrow transactions where damage was detected, ordered by most
    recent return first.  Includes damage_image in the response so the admin
    portal can display a "View Image" link.
    """
    stmt = (
        select(BorrowTransaction)
        .where(BorrowTransaction.damage_detected == True)  # noqa: E712
        .options(joinedload(BorrowTransaction.user), joinedload(BorrowTransaction.book))
        .order_by(BorrowTransaction.returned_at.desc())
    )
    records = db.scalars(stmt).all()

    results = []
    for tx in records:
        rec = _format_borrow_record(tx)
        # Attach the base64 image so the admin can view it
        rec.damage_image = tx.damage_image
        results.append(rec)
    return results


def get_damage_summary(db: Session) -> DamageSummaryResponse:
    """Return aggregate stats for damaged-book returns."""
    damaged_count = db.scalar(
        select(func.count(BorrowTransaction.id)).where(
            BorrowTransaction.damage_detected == True  # noqa: E712
        )
    ) or 0

    total_damage_fines = db.scalar(
        select(func.coalesce(func.sum(BorrowTransaction.fine_amount), 0.0)).where(
            BorrowTransaction.damage_detected == True  # noqa: E712
        )
    ) or 0.0

    return DamageSummaryResponse(
        damaged_count=int(damaged_count),
        total_damage_fines=round(float(total_damage_fines), 2),
    )
