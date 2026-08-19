from __future__ import annotations

from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base


class BorrowTransaction(Base):
    __tablename__ = "borrow_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    roll_number: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.roll_number", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    isbn10: Mapped[str] = mapped_column(
        String,
        ForeignKey("books.isbn10", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    borrowed_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )
    due_date: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )
    returned_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="active",
        server_default="active",
        nullable=False,
        index=True,
    )  # "active", "returned", "overdue"

    # Fine attributes
    fine_amount: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        server_default="0.0",
        nullable=False,
    )
    fine_paid: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        server_default="0.0",
        nullable=False,
    )
    fine_waived: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        server_default="0.0",
        nullable=False,
    )
    fine_reason: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    fine_status: Mapped[str] = mapped_column(
        String(32),
        default="none",
        server_default="none",
        nullable=False,
    )  # "none", "imposed", "paid", "waived", "partial"

    # Damage detection attributes (added for damaged-book return flow)
    damage_detected: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    damage_types: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )  # Comma-separated Roboflow class labels e.g. "torn,stained"
    damage_image: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )  # Base64-encoded image for admin preview

    user: Mapped["User"] = relationship("User", back_populates="borrows")
    book: Mapped["Book"] = relationship("Book", back_populates="borrows")

    @property
    def fine_remaining(self) -> float:
        return max(0.0, (self.fine_amount or 0.0) - (self.fine_paid or 0.0) - (self.fine_waived or 0.0))
