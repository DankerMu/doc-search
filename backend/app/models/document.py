from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, ForeignKey, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base

# Association table
document_tags = Table(
    "document_tags",
    Base.metadata,
    Column("document_id", ForeignKey("documents.id"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id"), primary_key=True),
)

DocumentTag = document_tags


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)  # stored filename
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # extracted text
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)  # pdf, docx, etc
    file_size: Mapped[int] = mapped_column(nullable=False)  # bytes
    folder_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("folders.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    folder = relationship("Folder", back_populates="documents")
    tags = relationship("Tag", secondary=document_tags, back_populates="documents")

