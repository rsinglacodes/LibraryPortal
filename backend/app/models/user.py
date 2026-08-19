from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base


class User(Base):
    __tablename__ = "users"

    roll_number: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    ratings: Mapped[list["Rating"]] = relationship(
        "Rating",
        back_populates="user",
    )
    borrows: Mapped[list["BorrowTransaction"]] = relationship(
        "BorrowTransaction",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    conversations: Mapped[list["ChatConversation"]] = relationship(
        "ChatConversation",
        back_populates="user",
        cascade="all, delete-orphan",
    )

