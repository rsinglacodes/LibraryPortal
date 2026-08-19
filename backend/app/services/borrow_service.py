from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status

from app.models.book import Book
from app.models.borrow import BorrowTransaction
from app.models.interaction import UserInteraction
from app.models.user import User
from app.schemas.admin import BorrowRecordResponse, ReturnWithInspectionResponse
from app.services.admin_service import _format_borrow_record, _get_now


def get_user_borrows(db: Session, roll_number: str) -> list[BorrowRecordResponse]:
    stmt = (
        select(BorrowTransaction)
        .where(BorrowTransaction.roll_number == roll_number)
        .options(joinedload(BorrowTransaction.user), joinedload(BorrowTransaction.book))
        .order_by(BorrowTransaction.borrowed_at.desc())
    )
    records = db.scalars(stmt).all()
    return [_format_borrow_record(r) for r in records]


def student_borrow_book(db: Session, roll_number: str, isbn10: str, days: int = 14) -> BorrowRecordResponse:
    user = db.get(User, roll_number)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with roll number '{roll_number}' not found",
        )

    book = db.get(Book, isbn10.strip())
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book with ISBN '{isbn10}' not found",
        )

    # Check if student already has active loan for this book
    existing = db.scalar(
        select(BorrowTransaction).where(
            BorrowTransaction.roll_number == roll_number,
            BorrowTransaction.isbn10 == isbn10.strip(),
            BorrowTransaction.status == "active",
        )
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have an active loan for this book",
        )

    # Check if student has unpaid overdue fines exceeding threshold (e.g. > $50)
    borrows = db.scalars(
        select(BorrowTransaction).where(BorrowTransaction.roll_number == roll_number)
    ).all()
    total_unpaid = sum(b.fine_remaining for b in borrows)
    if total_unpaid >= 50.0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Borrowing blocked: You have ${total_unpaid:.2f} in unpaid fines. Please clear your fines with the librarian.",
        )

    # Check real-time dynamic availability (total copies minus active loans)
    from sqlalchemy import func
    active_loans = db.scalar(
        select(func.count(BorrowTransaction.id)).where(
            BorrowTransaction.isbn10 == isbn10.strip(),
            BorrowTransaction.status == "active",
        )
    ) or 0
    tot_copies = book.total_copies if (book.total_copies is not None) else 5
    available_copies = max(0, tot_copies - active_loans)

    if available_copies <= 0:
        try:
            db.add(UserInteraction(
                roll_number=roll_number,
                interaction_type="borrow_attempt_unavailable",
                content=f"Attempted to borrow unavailable book: {book.title}",
                isbn10=book.isbn10,
            ))
            db.commit()
        except Exception:
            db.rollback()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot borrow '{book.title}': All {tot_copies} copies are currently checked out (0 available).",
        )

    now = _get_now()
    due = now + timedelta(days=days)


    tx = BorrowTransaction(
        roll_number=roll_number,
        isbn10=isbn10.strip(),
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

    # Track interaction
    try:
        db.add(UserInteraction(
            roll_number=roll_number,
            interaction_type="borrow",
            content=f"Borrowed {book.title}",
            isbn10=book.isbn10,
        ))
        db.commit()
    except Exception:
        db.rollback()

    return _format_borrow_record(tx)


def student_return_book(db: Session, roll_number: str, borrow_id: int) -> BorrowRecordResponse:
    tx = db.get(BorrowTransaction, borrow_id)
    if not tx or tx.roll_number != roll_number:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Borrow record not found for your account",
        )

    if tx.status == "returned":
        return _format_borrow_record(tx)

    now = _get_now()
    tx.returned_at = now
    tx.status = "returned"

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


def student_return_book_with_inspection(
    db: Session,
    roll_number: str,
    borrow_id: int,
    damage_detected: bool,
    damage_types: list[str],
    damage_image_b64: str,
) -> ReturnWithInspectionResponse:
    """
    Return a book that has been through the Roboflow damage inspection.

    Idempotent: if the transaction is already returned, returns the existing
    record without applying additional fines.

    Fine logic (backend-authoritative — frontend never sends fine amounts):
        damage_detected=True  → adds ₹100 damage fine on top of any overdue fine
        damage_detected=False → no damage fine
    """
    tx = db.get(BorrowTransaction, borrow_id)
    if not tx or tx.roll_number != roll_number:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Borrow record not found for your account",
        )

    # Idempotency: already returned → return existing record, no new fine
    if tx.status == "returned":
        rec = _format_borrow_record(tx)
        return ReturnWithInspectionResponse(
            borrow_record=rec,
            condition="damaged" if tx.damage_detected else "good",
            damage_detected=bool(tx.damage_detected),
            damage_types=tx.damage_types,
            fine_applied=0.0,
        )

    now = _get_now()
    tx.returned_at = now
    tx.status = "returned"

    # ── Overdue fine (existing logic, unchanged) ──────────────────────────────
    overdue_fine_applied = 0.0
    if tx.due_date and now > tx.due_date:
        overdue_days = max(1, (now - tx.due_date).days)
        late_fee = round(10.0 + (overdue_days * 10.0), 2)
        if (tx.fine_amount or 0.0) < late_fee:
            tx.fine_amount = late_fee
            tx.fine_reason = f"Overdue fine: ₹10 base + ₹10/day ({overdue_days} day{'s' if overdue_days > 1 else ''} late)"
            if tx.fine_status in ("none", None):
                tx.fine_status = "imposed"
            overdue_fine_applied = late_fee

    # ── Damage fine (new, backend-authoritative) ──────────────────────────────
    damage_fine_applied = 0.0
    if damage_detected:
        DAMAGE_FINE = 100.0
        tx.fine_amount = (tx.fine_amount or 0.0) + DAMAGE_FINE
        damage_fine_applied = DAMAGE_FINE
        existing_reason = tx.fine_reason or ""
        damage_reason_part = "Book damage fine: ₹100 (damage detected on return)"
        tx.fine_reason = f"{existing_reason}; {damage_reason_part}".strip("; ")
        tx.fine_status = "imposed"

    # ── Store damage detection result ─────────────────────────────────────────
    tx.damage_detected = damage_detected
    tx.damage_types = ", ".join(damage_types) if damage_types else None
    tx.damage_image = damage_image_b64 if damage_image_b64 else None

    db.commit()
    db.refresh(tx)

    rec = _format_borrow_record(tx)
    condition = "damaged" if damage_detected else "good"

    return ReturnWithInspectionResponse(
        borrow_record=rec,
        condition=condition,
        damage_detected=damage_detected,
        damage_types=tx.damage_types,
        fine_applied=damage_fine_applied,
    )

