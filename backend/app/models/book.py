from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base


class Book(Base):
    __tablename__ = "books"

    isbn10: Mapped[str] = mapped_column(String, primary_key=True)
    isbn13: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    subtitle: Mapped[str | None] = mapped_column(String, nullable=True)
    authors: Mapped[str | None] = mapped_column(Text, nullable=True)
    categories: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    thumbnail: Mapped[str | None] = mapped_column(Text, nullable=True)
    publisher: Mapped[str | None] = mapped_column(String, nullable=True)
    published_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    num_pages: Mapped[int | None] = mapped_column(Integer, nullable=True)
    average_rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    ratings_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_copies: Mapped[int] = mapped_column(Integer, default=5, server_default="5")

    ratings: Mapped[list["Rating"]] = relationship(
        "Rating",
        back_populates="book",
        cascade="all, delete-orphan",
    )
    borrows: Mapped[list["BorrowTransaction"]] = relationship(
        "BorrowTransaction",
        back_populates="book",
        cascade="all, delete-orphan",
    )

