import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models import Document, Folder, Tag


@pytest.mark.asyncio
async def test_get_db_yields_session():
    async for session in get_db():
        assert session is not None
        break


@pytest.mark.asyncio
async def test_create_folder(test_db):
    async with test_db() as session:
        folder = Folder(name="Test Folder")
        session.add(folder)
        await session.commit()
        await session.refresh(folder)

        assert folder.id is not None
        assert folder.name == "Test Folder"


@pytest.mark.asyncio
async def test_create_tag(test_db):
    async with test_db() as session:
        tag = Tag(name="test-tag", color="#FF00FF")
        session.add(tag)
        await session.commit()
        await session.refresh(tag)

        assert tag.id is not None
        assert tag.name == "test-tag"
        assert tag.color == "#FF00FF"


@pytest.mark.asyncio
async def test_create_document(test_db):
    async with test_db() as session:
        document = Document(
            filename="stored.pdf",
            original_name="original.pdf",
            content_text="Hello",
            file_type="pdf",
            file_size=123,
        )
        session.add(document)
        await session.commit()
        await session.refresh(document)

        assert document.id is not None
        assert document.filename == "stored.pdf"
        assert document.original_name == "original.pdf"
        assert document.file_type == "pdf"
        assert document.file_size == 123
        assert document.created_at is not None
        assert document.updated_at is not None


@pytest.mark.asyncio
async def test_document_folder_relationship(test_db):
    async with test_db() as session:
        folder = Folder(name="Root")
        document = Document(
            filename="stored.txt",
            original_name="original.txt",
            content_text="Hi",
            file_type="txt",
            file_size=1,
            folder=folder,
        )
        session.add_all([folder, document])
        await session.commit()

        result = await session.execute(
            select(Document)
            .options(selectinload(Document.folder))
            .where(Document.id == document.id)
        )
        db_document = result.scalar_one()
        assert db_document.folder is not None
        assert db_document.folder.id == folder.id

        result = await session.execute(
            select(Folder)
            .options(selectinload(Folder.documents))
            .where(Folder.id == folder.id)
        )
        db_folder = result.scalar_one()
        assert [doc.id for doc in db_folder.documents] == [document.id]


@pytest.mark.asyncio
async def test_document_tag_many_to_many(test_db):
    async with test_db() as session:
        tag1 = Tag(name="t1", color="#111111")
        tag2 = Tag(name="t2")
        document = Document(
            filename="stored.md",
            original_name="original.md",
            content_text="Tags",
            file_type="md",
            file_size=10,
            tags=[tag1, tag2],
        )
        session.add(document)
        await session.commit()

        result = await session.execute(
            select(Document)
            .options(selectinload(Document.tags))
            .where(Document.id == document.id)
        )
        db_document = result.scalar_one()
        assert sorted(tag.name for tag in db_document.tags) == ["t1", "t2"]

        result = await session.execute(
            select(Tag).options(selectinload(Tag.documents)).where(Tag.id == tag1.id)
        )
        db_tag = result.scalar_one()
        assert [doc.id for doc in db_tag.documents] == [document.id]


@pytest.mark.asyncio
async def test_folder_parent_child_relationship(test_db):
    async with test_db() as session:
        parent = Folder(name="Parent")
        child = Folder(name="Child", parent=parent)
        session.add_all([parent, child])
        await session.commit()

        result = await session.execute(
            select(Folder)
            .options(selectinload(Folder.children))
            .where(Folder.id == parent.id)
        )
        db_parent = result.scalar_one()
        assert [folder.name for folder in db_parent.children] == ["Child"]

        result = await session.execute(
            select(Folder)
            .options(selectinload(Folder.parent))
            .where(Folder.id == child.id)
        )
        db_child = result.scalar_one()
        assert db_child.parent is not None
        assert db_child.parent.id == parent.id
