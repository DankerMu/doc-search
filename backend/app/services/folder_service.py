from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Document, Folder

try:
    from app.services.search_service import get_search_service
except ModuleNotFoundError as exc:  # pragma: no cover
    if exc.name and (exc.name == "jieba" or exc.name.startswith("whoosh")):
        get_search_service = None  # type: ignore[assignment]
    else:
        raise

MAX_FOLDER_DEPTH = 5


class FolderService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_folder(self, name: str, parent_id: Optional[int] = None) -> Folder:
        # Validate parent exists
        if parent_id:
            parent = await self.get_folder(parent_id)
            if not parent:
                raise ValueError("Parent folder not found")
            depth = await self._get_depth(parent_id)
            if depth >= MAX_FOLDER_DEPTH:
                raise ValueError(f"Maximum folder depth ({MAX_FOLDER_DEPTH}) exceeded")

        folder = Folder(name=name, parent_id=parent_id)
        self.db.add(folder)
        await self.db.commit()
        await self.db.refresh(folder)
        return folder

    async def get_folder(self, folder_id: int) -> Optional[Folder]:
        result = await self.db.execute(select(Folder).where(Folder.id == folder_id))
        return result.scalar_one_or_none()

    async def update_folder(self, folder_id: int, name: str) -> Optional[Folder]:
        folder = await self.get_folder(folder_id)
        if not folder:
            return None
        folder.name = name
        await self.db.commit()
        await self.db.refresh(folder)
        return folder

    async def delete_folder(self, folder_id: int) -> bool:
        folder = await self.get_folder(folder_id)
        if not folder:
            return False

        # Get documents that will be moved to root
        doc_result = await self.db.execute(
            select(Document).where(Document.folder_id == folder_id)
        )
        affected_docs = list(doc_result.scalars().all())

        # Move documents to root (folder_id = None)
        await self.db.execute(
            Document.__table__.update()
            .where(Document.folder_id == folder_id)
            .values(folder_id=None)
        )

        # Move child folders to parent
        await self.db.execute(
            Folder.__table__.update()
            .where(Folder.parent_id == folder_id)
            .values(parent_id=folder.parent_id)
        )

        await self.db.delete(folder)
        await self.db.commit()

        # Reindex affected documents with updated folder_id
        if get_search_service is not None and affected_docs:
            try:
                search_service = get_search_service()
                for doc in affected_docs:
                    search_service.index_document(
                        doc_id=doc.id,
                        content=doc.content_text or "",
                        file_type=doc.file_type,
                        folder_id=None,  # Now moved to root
                        tag_ids=[],
                        created_at=doc.created_at,
                    )
            except Exception:
                pass

        return True

    async def get_folder_tree(self) -> List[dict]:
        result = await self.db.execute(select(Folder).order_by(Folder.name))
        folders = result.scalars().all()
        return self._build_tree(folders, None)

    def _build_tree(
        self, folders: List[Folder], parent_id: Optional[int]
    ) -> List[dict]:
        tree = []
        for folder in folders:
            if folder.parent_id == parent_id:
                tree.append(
                    {
                        "id": folder.id,
                        "name": folder.name,
                        "parent_id": folder.parent_id,
                        "children": self._build_tree(folders, folder.id),
                    }
                )
        return tree

    async def _get_depth(self, folder_id: int) -> int:
        depth = 1
        current_id = folder_id
        while current_id:
            folder = await self.get_folder(current_id)
            if not folder or not folder.parent_id:
                break
            current_id = folder.parent_id
            depth += 1
        return depth
