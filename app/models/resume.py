from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User

class Resume(Base):
    __tablename__ = "resumes"
    
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )
    
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    ) 
    
    file_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    
    file_size_bytes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    
    extracted_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    
    user: Mapped["User"] = relationship(
        back_populates="resumes",
    )