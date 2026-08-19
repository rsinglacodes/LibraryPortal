from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base


class Rating(Base):
    __tablename__ = "ratings"
    __table_args__ = (
        UniqueConstraint("roll_number", "isbn10", name="uq_rating_user_book"),
    )

    rating_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    roll_number: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.roll_number"),
        nullable=False,
    )
    isbn10: Mapped[str] = mapped_column(
        String,
        ForeignKey("books.isbn10"),
        nullable=False,
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    review: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="ratings")
    book: Mapped["Book"] = relationship("Book", back_populates="ratings")

