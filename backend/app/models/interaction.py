from __future__ import annotations

from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class UserInteraction(Base):
    __tablename__ = "user_interactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    roll_number: Mapped[str] = mapped_column(String(64), index=True)
    interaction_type: Mapped[str] = mapped_column(String(32), index=True)  # 'search', 'chat', 'view', 'explore'
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    isbn10: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
