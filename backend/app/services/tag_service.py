from __future__ import annotations

from typing import List, Optional

from sqlalchemy import delete, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Document, Tag
from app.models.document import document_tags

try:
    from app.services.search_service import get_search_service
except ModuleNotFoundError as exc:  # pragma: no cover
    if exc.name and (exc.name == "jieba" or exc.name.startswith("whoosh")):
        get_search_service = None  # type: ignore[assignment]
    else:
        raise


class TagService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_tag(self, name: str, color: str = "#3B82F6") -> Tag:
        tag = Tag(name=name, color=color)
        self.db.add(tag)
        await self.db.commit()
        await self.db.refresh(tag)
        return tag

    async def get_tag(self, tag_id: int) -> Optional[Tag]:
        result = await self.db.execute(select(Tag).where(Tag.id == tag_id))
        return result.scalar_one_or_none()

    async def get_tag_by_name(self, name: str) -> Optional[Tag]:
        result = await self.db.execute(select(Tag).where(Tag.name == name))
        return result.scalar_one_or_none()

    async def update_tag(
        self, tag_id: int, name: Optional[str] = None, color: Optional[str] = None
    ) -> Optional[Tag]:
        tag = await self.get_tag(tag_id)
        if not tag:
            return None
        if name is not None:
            tag.name = name
        if color is not None:
            tag.color = color
        await self.db.commit()
        await self.db.refresh(tag)
        return tag

    async def delete_tag(self, tag_id: int) -> bool:
        tag = await self.get_tag(tag_id)
        if not tag:
            return False

        # Get affected documents before deleting tag
        doc_result = await self.db.execute(
            select(Document)
            .join(document_tags, Document.id == document_tags.c.document_id)
            .where(document_tags.c.tag_id == tag_id)
            .options(selectinload(Document.tags))
        )
        affected_docs = list(doc_result.scalars().all())

        await self.db.delete(tag)
        await self.db.commit()

        # Reindex documents that had this tag removed
        if get_search_service is not None and affected_docs:
            try:
                search_service = get_search_service()
                for doc in affected_docs:
                    # Re-fetch tag_ids excluding the deleted tag
                    remaining_tag_ids = [t.id for t in doc.tags if t.id != tag_id]
                    search_service.index_document(
                        doc_id=doc.id,
                        content=doc.content_text or "",
                        file_type=doc.file_type,
                        folder_id=doc.folder_id,
                        tag_ids=remaining_tag_ids,
                        created_at=doc.created_at,
                    )
            except Exception:
                pass

        return True

    async def list_tags(self) -> List[dict]:
        result = await self.db.execute(select(Tag).order_by(Tag.name))
        tags = result.scalars().all()

        # Get document counts for each tag
        count_result = await self.db.execute(
            select(
                document_tags.c.tag_id,
                func.count(document_tags.c.document_id).label("doc_count"),
            ).group_by(document_tags.c.tag_id)
        )
        counts = {row.tag_id: row.doc_count for row in count_result}

        return [
            {
                "id": tag.id,
                "name": tag.name,
                "color": tag.color,
                "document_count": counts.get(tag.id, 0),
                "created_at": tag.created_at,
            }
            for tag in tags
        ]

    async def add_tag_to_document(self, document_id: int, tag_id: int) -> bool:
        # Check document exists
        doc_result = await self.db.execute(
            select(Document)
            .where(Document.id == document_id)
            .options(selectinload(Document.tags))
        )
        doc = doc_result.scalar_one_or_none()
        if not doc:
            raise ValueError("Document not found")

        # Check tag exists
        tag = await self.get_tag(tag_id)
        if not tag:
            raise ValueError("Tag not found")

        # Check if already linked
        existing = await self.db.execute(
            select(document_tags).where(
                document_tags.c.document_id == document_id,
                document_tags.c.tag_id == tag_id,
            )
        )
        if existing.first():
            return False  # Already tagged

        await self.db.execute(
            insert(document_tags).values(document_id=document_id, tag_id=tag_id)
        )
        await self.db.commit()

        # Reindex document with new tag
        if get_search_service is not None:
            try:
                search_service = get_search_service()
                tag_ids = [t.id for t in doc.tags] + [tag_id]
                search_service.index_document(
                    doc_id=doc.id,
                    content=doc.content_text or "",
                    file_type=doc.file_type,
                    folder_id=doc.folder_id,
                    tag_ids=tag_ids,
                    created_at=doc.created_at,
                )
            except Exception:
                pass

        return True

    async def remove_tag_from_document(self, document_id: int, tag_id: int) -> bool:
        # Check document exists
        doc_result = await self.db.execute(
            select(Document)
            .where(Document.id == document_id)
            .options(selectinload(Document.tags))
        )
        doc = doc_result.scalar_one_or_none()
        if not doc:
            raise ValueError("Document not found")

        result = await self.db.execute(
            delete(document_tags).where(
                document_tags.c.document_id == document_id,
                document_tags.c.tag_id == tag_id,
            )
        )
        await self.db.commit()

        if result.rowcount == 0:
            return False

        # Reindex document with tag removed
        if get_search_service is not None:
            try:
                search_service = get_search_service()
                tag_ids = [t.id for t in doc.tags if t.id != tag_id]
                search_service.index_document(
                    doc_id=doc.id,
                    content=doc.content_text or "",
                    file_type=doc.file_type,
                    folder_id=doc.folder_id,
                    tag_ids=tag_ids,
                    created_at=doc.created_at,
                )
            except Exception:
                pass

        return True

    async def batch_add_tags(
        self, document_ids: List[int], tag_ids: List[int]
    ) -> dict:
        added = 0
        skipped = 0

        tag_ids = list(set(tag_ids))

        # Validate all tags exist
        for tag_id in tag_ids:
            tag = await self.get_tag(tag_id)
            if not tag:
                raise ValueError(f"Tag {tag_id} not found")

        for doc_id in document_ids:
            doc_result = await self.db.execute(
                select(Document)
                .where(Document.id == doc_id)
                .options(selectinload(Document.tags))
            )
            doc = doc_result.scalar_one_or_none()
            if not doc:
                continue

            # Query existing tags directly from association table to avoid ORM cache issues
            existing_result = await self.db.execute(
                select(document_tags.c.tag_id).where(
                    document_tags.c.document_id == doc_id
                )
            )
            current_tag_ids = {row.tag_id for row in existing_result}

            for tag_id in tag_ids:
                if tag_id in current_tag_ids:
                    skipped += 1
                    continue

                await self.db.execute(
                    insert(document_tags).values(document_id=doc_id, tag_id=tag_id)
                )
                added += 1

            # Reindex document
            if get_search_service is not None:
                try:
                    search_service = get_search_service()
                    new_tag_ids = list(current_tag_ids | set(tag_ids))
                    search_service.index_document(
                        doc_id=doc.id,
                        content=doc.content_text or "",
                        file_type=doc.file_type,
                        folder_id=doc.folder_id,
                        tag_ids=new_tag_ids,
                        created_at=doc.created_at,
                    )
                except Exception:
                    pass

        await self.db.commit()
        return {"added": added, "skipped": skipped}

    async def batch_remove_tags(
        self, document_ids: List[int], tag_ids: List[int]
    ) -> dict:
        removed = 0

        for doc_id in document_ids:
            doc_result = await self.db.execute(
                select(Document)
                .where(Document.id == doc_id)
                .options(selectinload(Document.tags))
            )
            doc = doc_result.scalar_one_or_none()
            if not doc:
                continue

            for tag_id in tag_ids:
                result = await self.db.execute(
                    delete(document_tags).where(
                        document_tags.c.document_id == doc_id,
                        document_tags.c.tag_id == tag_id,
                    )
                )
                removed += result.rowcount

            # Reindex document
            if get_search_service is not None:
                try:
                    search_service = get_search_service()
                    remaining_tag_ids = [
                        t.id for t in doc.tags if t.id not in tag_ids
                    ]
                    search_service.index_document(
                        doc_id=doc.id,
                        content=doc.content_text or "",
                        file_type=doc.file_type,
                        folder_id=doc.folder_id,
                        tag_ids=remaining_tag_ids,
                        created_at=doc.created_at,
                    )
                except Exception:
                    pass

        await self.db.commit()
        return {"removed": removed}
