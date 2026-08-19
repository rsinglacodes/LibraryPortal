from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_admin
from app.database.connection import get_db
from app.models.user import User
from app.schemas.admin import (
    AdminOverviewResponse,
    BorrowRecordResponse,
    CreateBookRequest,
    DamageSummaryResponse,
    DemandAnalyticsResponse,
    ImposeFineRequest,
    IssueBookRequest,
    PayFineRequest,
    ReturnBookRequest,
    UpdateBookRequest,
    UserFineSummaryResponse,
    WaiveFineRequest,
)
from app.schemas.book import BookResponse
from app.services import admin_service
from app.services.book_service import _format_book_item

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/overview", response_model=AdminOverviewResponse)
def get_overview(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> AdminOverviewResponse:
    return admin_service.get_admin_overview(db)


@router.get("/borrows", response_model=list[BorrowRecordResponse])
def get_all_borrows(
    status: Optional[str] = Query(None, description="Filter by status: active, overdue, returned, fines"),
    q: Optional[str] = Query(None, description="Search by roll number, name, book title or ISBN"),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> list[BorrowRecordResponse]:
    return admin_service.list_borrows(db, status_filter=status, q=q)


@router.post("/borrows/issue", response_model=BorrowRecordResponse, status_code=status.HTTP_201_CREATED)
def issue_book_to_student(
    payload: IssueBookRequest,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> BorrowRecordResponse:
    return admin_service.issue_book(db, payload)


@router.post("/borrows/{borrow_id}/return", response_model=BorrowRecordResponse)
def return_borrowed_book(
    borrow_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> BorrowRecordResponse:
    return admin_service.return_book(db, borrow_id)


@router.get("/fines", response_model=list[UserFineSummaryResponse])
def get_fines_directory(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> list[UserFineSummaryResponse]:
    return admin_service.get_fines_summary(db)


@router.post("/fines/impose", response_model=BorrowRecordResponse)
def impose_fine_on_user(
    payload: ImposeFineRequest,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> BorrowRecordResponse:
    return admin_service.impose_fine(db, payload)


@router.post("/fines/waive", response_model=list[BorrowRecordResponse])
def waive_or_remove_fine(
    payload: WaiveFineRequest,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> list[BorrowRecordResponse]:
    return admin_service.waive_fine(db, payload)


@router.post("/fines/pay", response_model=list[BorrowRecordResponse])
def record_fine_payment(
    payload: PayFineRequest,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> list[BorrowRecordResponse]:
    return admin_service.pay_fine(db, payload)


@router.get("/analytics/demand", response_model=DemandAnalyticsResponse)
def get_demand_analytics(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> DemandAnalyticsResponse:
    return admin_service.get_demand_analytics(db)


@router.post("/books", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
def add_new_book(
    payload: CreateBookRequest,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> BookResponse:
    book = admin_service.create_book(db, payload)
    return _format_book_item(book, db=db)


@router.put("/books/{isbn10}", response_model=BookResponse)
def update_book_details(
    isbn10: str,
    payload: UpdateBookRequest,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> BookResponse:
    book = admin_service.update_book(db, isbn10, payload)
    return _format_book_item(book, db=db)


@router.delete("/books/{isbn10}")
def remove_book_from_catalog(
    isbn10: str,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return admin_service.delete_book(db, isbn10)


@router.get("/inventory/verify")
def verify_inventory_consistency(
    isbn10: Optional[str] = Query(None, description="Optional ISBN10 to verify specific book"),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    from app.core.inventory import recalculate_and_verify_inventory
    return recalculate_and_verify_inventory(db, isbn10)


# ── Damage-detection admin endpoints ─────────────────────────────────────────

@router.get("/damaged-returns", response_model=list[BorrowRecordResponse])
def get_damaged_returns(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> list[BorrowRecordResponse]:
    """Return all borrow transactions where book damage was detected on return."""
    return admin_service.get_damaged_returns(db)


@router.get("/damage-summary", response_model=DamageSummaryResponse)
def get_damage_summary(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> DamageSummaryResponse:
    """Return aggregate counts and total fines for damaged-book returns."""
    return admin_service.get_damage_summary(db)
