from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional


class AdminOverviewResponse(BaseModel):
    total_users: int
    total_books: int
    active_borrows: int
    overdue_borrows: int
    total_fines_imposed: float
    total_fines_paid: float
    total_fines_waived: float
    total_fines_remaining: float


class BorrowRecordResponse(BaseModel):
    id: int
    roll_number: str
    user_name: str
    user_email: str
    isbn10: str
    book_title: str
    book_authors: Optional[str] = None
    book_thumbnail: Optional[str] = None
    borrowed_at: datetime
    due_date: datetime
    returned_at: Optional[datetime] = None
    status: str  # "active", "returned", "overdue"
    fine_amount: float
    fine_paid: float
    fine_waived: float
    fine_remaining: float
    fine_reason: Optional[str] = None
    fine_status: str
    damage_detected: bool = False
    damage_types: Optional[str] = None
    damage_image: Optional[str] = None  # base64 string, only present in admin damaged-return responses


class IssueBookRequest(BaseModel):
    roll_number: str
    isbn10: str
    days: int = 14


class ReturnBookRequest(BaseModel):
    borrow_id: int


class ImposeFineRequest(BaseModel):
    roll_number: str
    borrow_id: Optional[int] = None
    amount: float = Field(gt=0, description="Fine amount to impose")
    reason: str = Field(min_length=3, max_length=255, description="Reason for imposing fine")


class WaiveFineRequest(BaseModel):
    borrow_id: Optional[int] = None
    roll_number: Optional[str] = None
    amount: Optional[float] = Field(None, gt=0, description="Amount to waive (if None, waives all remaining fine)")
    reason: Optional[str] = "Waived by librarian / admin"


class PayFineRequest(BaseModel):
    borrow_id: Optional[int] = None
    roll_number: Optional[str] = None
    amount: float = Field(gt=0, description="Amount paid")


class UserLoanItem(BaseModel):
    borrow_id: int
    isbn10: str
    book_title: str
    book_authors: Optional[str] = None
    book_thumbnail: Optional[str] = None
    quantity: int = 1
    borrowed_at: datetime
    due_date: datetime
    returned_at: Optional[datetime] = None
    status: str
    fine_amount: float
    fine_paid: float
    fine_waived: float
    fine_remaining: float
    fine_reason: Optional[str] = None


class UserFineSummaryResponse(BaseModel):
    roll_number: str
    name: str
    email: str
    active_borrows_count: int
    total_borrows_count: int
    total_fines_imposed: float
    total_fines_paid: float
    total_fines_waived: float
    total_fines_remaining: float
    loans: list[UserLoanItem] = []


class BookDemandItem(BaseModel):
    isbn10: str
    title: str
    authors: Optional[str] = None
    categories: Optional[str] = None
    thumbnail: Optional[str] = None
    average_rating: Optional[float] = None
    ratings_count: Optional[int] = None
    total_copies: int
    copies_available: int
    borrow_count: int
    search_interaction_count: int
    unmet_demand_count: int = 0  # interest shown when book was unavailable
    demand_score: float
    restock_status: str  # "URGENT_RESTOCK", "LOW_STOCK", "OPTIMAL", "LOW_DEMAND", "OVERSTOCKED"
    recommended_restock_qty: int


class DemandAnalyticsResponse(BaseModel):
    top_demanding: list[BookDemandItem]
    least_demanding: list[BookDemandItem]



class CreateBookRequest(BaseModel):
    isbn10: str = Field(min_length=1, max_length=20)
    isbn13: Optional[str] = Field(None, max_length=20)
    title: str = Field(min_length=1, max_length=500)
    subtitle: Optional[str] = None
    authors: Optional[str] = None
    categories: Optional[str] = None
    description: Optional[str] = None
    thumbnail: Optional[str] = None
    publisher: Optional[str] = None
    published_year: Optional[int] = None
    num_pages: Optional[int] = None
    total_copies: int = Field(default=5, ge=1, le=100)


class UpdateBookRequest(BaseModel):
    title: Optional[str] = None
    subtitle: Optional[str] = None
    authors: Optional[str] = None
    categories: Optional[str] = None
    description: Optional[str] = None
    thumbnail: Optional[str] = None
    publisher: Optional[str] = None
    published_year: Optional[int] = None
    num_pages: Optional[int] = None
    total_copies: Optional[int] = Field(None, ge=1, le=100)


# ── Damage-detection schemas ─────────────────────────────────────────────────

class ReturnWithInspectionResponse(BaseModel):
    """Returned by POST /borrows/return-with-inspection/{borrow_id}."""
    borrow_record: BorrowRecordResponse
    condition: str            # "good" | "damaged"
    damage_detected: bool
    damage_types: Optional[str] = None  # comma-separated labels
    fine_applied: float       # 0.0 or 100.0


class DamageSummaryResponse(BaseModel):
    """Returned by GET /admin/damage-summary."""
    damaged_count: int
    total_damage_fines: float
