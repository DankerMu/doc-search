from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..models import Document
from .parser import DocumentParser


class DocumentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def save_document(
        self,
        original_name: str,
        content: bytes,
        file_type: str,
        folder_id: Optional[int] = None,
    ) -> Document:
        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)

        safe_original_name = Path(original_name).name
        normalized_type = file_type.lower()
        suffix = f".{normalized_type}" if normalized_type else ""
        stored_filename = f"{uuid.uuid4().hex}{suffix}"
        file_path = upload_dir / stored_filename

        await asyncio.to_thread(file_path.write_bytes, content)
        content_text, _is_encrypted = await asyncio.to_thread(
            DocumentParser.parse, file_path, normalized_type
        )

        document = Document(
            filename=stored_filename,
            original_name=safe_original_name,
            content_text=content_text,
            file_type=normalized_type,
            file_size=len(content),
            folder_id=folder_id,
        )
        self.db.add(document)
        await self.db.commit()
        await self.db.refresh(document)
        return document

    async def get_document(self, document_id: int) -> Optional[Document]:
        return await self.db.get(Document, document_id)

    async def list_documents(
        self, folder_id: Optional[int], skip: int, limit: int
    ) -> tuple[list[Document], int]:
        query = select(Document)
        count_query = select(func.count()).select_from(Document)

        if folder_id is not None:
            query = query.where(Document.folder_id == folder_id)
            count_query = count_query.where(Document.folder_id == folder_id)

        query = query.order_by(Document.created_at.desc()).offset(skip).limit(limit)

        result = await self.db.execute(query)
        items = list(result.scalars().all())

        total_result = await self.db.execute(count_query)
        total = int(total_result.scalar_one())

        return items, total

    async def delete_document(self, document_id: int) -> bool:
        document = await self.get_document(document_id)
        if document is None:
            return False

        file_path = Path(settings.UPLOAD_DIR) / document.filename
        await self.db.delete(document)
        await self.db.commit()

        await asyncio.to_thread(self._safe_delete_file, file_path)
        return True

    @staticmethod
    def _safe_delete_file(path: Path) -> None:
        try:
            path.unlink()
        except FileNotFoundError:
            return
        except Exception:
            return
