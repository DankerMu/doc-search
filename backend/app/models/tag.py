from __future__ import annotations

from datetime import datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base
from .document import document_tags


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    color: Mapped[str] = mapped_column(String(7), default="#3B82F6")  # hex color
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    documents = relationship(
        "Document",
        secondary=document_tags,
        back_populates="tags",
    )

