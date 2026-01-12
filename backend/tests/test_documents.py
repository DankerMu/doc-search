from __future__ import annotations

from pathlib import Path

import pytest
from httpx import AsyncClient

import app.routers.documents as documents_router
import app.services.document_service as document_service_module
from app.core.config import settings
from app.models import Document, Folder
from app.services.document_service import DocumentService


@pytest.fixture
def upload_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    upload_dir = tmp_path / "uploads"
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(upload_dir))
    return upload_dir


@pytest.fixture
def inline_to_thread(monkeypatch: pytest.MonkeyPatch):
    async def _to_thread(func, /, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(document_service_module.asyncio, "to_thread", _to_thread)


@pytest.fixture
def markdown_upload() -> tuple[str, bytes, str]:
    return ("nested/hello.md", b"Hello", "text/markdown")


@pytest.mark.asyncio
async def test_upload_document(
    client: AsyncClient,
    test_db,
    upload_dir: Path,
    inline_to_thread,
    markdown_upload: tuple[str, bytes, str],
):
    filename, content, content_type = markdown_upload
    response = await client.post(
        "/api/documents/upload",
        files={"file": (filename, content, content_type)},
    )
    assert response.status_code == 200

    payload = response.json()
    assert isinstance(payload["id"], int)
    assert payload["filename"].endswith(".md")
    assert payload["original_name"] == "hello.md"
    assert payload["file_type"] == "md"
    assert payload["file_size"] == len(content)
    assert payload["folder_id"] is None
    assert payload["created_at"]

    stored_path = upload_dir / payload["filename"]
    assert stored_path.is_file()
    assert stored_path.read_bytes() == content

    async with test_db() as session:
        doc = await session.get(Document, payload["id"])
        assert doc is not None
        assert doc.content_text == content.decode("utf-8")


@pytest.mark.asyncio
async def test_upload_unsupported_type(client: AsyncClient):
    response = await client.post(
        "/api/documents/upload",
        files={"file": ("malware.exe", b"nope", "application/octet-stream")},
    )
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_file_too_large(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(documents_router, "MAX_FILE_SIZE", 4)
    response = await client.post(
        "/api/documents/upload",
        files={"file": ("big.md", b"12345", "text/markdown")},
    )
    assert response.status_code == 400
    assert "File too large" in response.json()["detail"]


@pytest.mark.asyncio
async def test_list_documents(
    client: AsyncClient,
    upload_dir: Path,
    inline_to_thread,
):
    await client.post(
        "/api/documents/upload",
        files={"file": ("a.md", b"A", "text/markdown")},
    )
    await client.post(
        "/api/documents/upload",
        files={"file": ("b.md", b"B", "text/markdown")},
    )

    response = await client.get("/api/documents")
    assert response.status_code == 200

    payload = response.json()
    assert payload["total"] == 2
    assert len(payload["items"]) == 2
    assert {item["original_name"] for item in payload["items"]} == {"a.md", "b.md"}


@pytest.mark.asyncio
async def test_get_document(
    client: AsyncClient,
    upload_dir: Path,
    inline_to_thread,
):
    upload = await client.post(
        "/api/documents/upload",
        files={"file": ("one.md", b"One", "text/markdown")},
    )
    doc_id = upload.json()["id"]

    response = await client.get(f"/api/documents/{doc_id}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == doc_id
    assert payload["original_name"] == "one.md"


@pytest.mark.asyncio
async def test_get_document_not_found(client: AsyncClient):
    response = await client.get("/api/documents/999999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found"


@pytest.mark.asyncio
async def test_delete_document(
    client: AsyncClient,
    upload_dir: Path,
    inline_to_thread,
):
    upload = await client.post(
        "/api/documents/upload",
        files={"file": ("del.md", b"Delete me", "text/markdown")},
    )
    stored_filename = upload.json()["filename"]
    doc_id = upload.json()["id"]

    stored_path = upload_dir / stored_filename
    assert stored_path.is_file()

    response = await client.delete(f"/api/documents/{doc_id}")
    assert response.status_code == 200
    assert response.json() == {"message": "Document deleted"}
    assert stored_path.exists() is False

    response = await client.get(f"/api/documents/{doc_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_document_not_found(client: AsyncClient):
    response = await client.delete("/api/documents/999999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found"


@pytest.mark.asyncio
async def test_document_service_list_documents_filters_folder(test_db):
    async with test_db() as session:
        folder = Folder(name="Filter folder")
        session.add(folder)
        await session.commit()
        await session.refresh(folder)

        session.add_all(
            [
                Document(
                    filename="in-folder.md",
                    original_name="in-folder.md",
                    content_text="In",
                    file_type="md",
                    file_size=2,
                    folder_id=folder.id,
                ),
                Document(
                    filename="outside.md",
                    original_name="outside.md",
                    content_text="Out",
                    file_type="md",
                    file_size=3,
                    folder_id=None,
                ),
            ]
        )
        await session.commit()

        service = DocumentService(session)
        items, total = await service.list_documents(folder.id, skip=0, limit=20)
        assert total == 1
        assert [doc.original_name for doc in items] == ["in-folder.md"]


@pytest.mark.asyncio
async def test_document_service_save_and_delete_document(
    test_db,
    upload_dir: Path,
    inline_to_thread,
    monkeypatch: pytest.MonkeyPatch,
):
    def dummy_parse(_file_path: Path, _file_type: str):
        return "Parsed text", False

    monkeypatch.setattr(document_service_module.DocumentParser, "parse", dummy_parse)

    async with test_db() as session:
        service = DocumentService(session)
        document = await service.save_document("nested/orig.MD", b"Hi", "MD")
        assert document.id is not None
        assert document.original_name == "orig.MD"
        assert document.file_type == "md"
        assert document.content_text == "Parsed text"

        stored_path = upload_dir / document.filename
        assert stored_path.is_file()

        assert await service.delete_document(999999) is False
        assert await service.delete_document(document.id) is True
        assert await session.get(Document, document.id) is None


def test_safe_delete_file_swallows_exceptions(tmp_path: Path):
    path = tmp_path / "exists.txt"
    path.write_text("x", encoding="utf-8")
    DocumentService._safe_delete_file(path)
    assert path.exists() is False

    class MissingPath:
        def unlink(self):
            raise FileNotFoundError

    DocumentService._safe_delete_file(MissingPath())  # should not raise

    class ExplodingPath:
        def unlink(self):
            raise RuntimeError("boom")

    DocumentService._safe_delete_file(ExplodingPath())  # should not raise
