from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.core.database as database_module
import app.routers.documents as documents_router
import app.routers.search as search_router
import app.services.document_service as document_service_module
import app.services.parser as parser_module
import app.services.search_service as search_service_module
from app.core.config import settings
from app.main import app, lifespan
from app.models import Document, Folder
from app.services.document_service import DocumentService
from app.services.folder_service import FolderService, MAX_FOLDER_DEPTH
from app.services.parser import DocumentParser
from app.services.search_service import SearchService


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
def search_service(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SearchService:
    index_dir = tmp_path / "search_index"
    monkeypatch.setattr(settings, "INDEX_DIR", str(index_dir))
    service = SearchService(index_dir=str(index_dir))
    monkeypatch.setattr(search_service_module, "_search_service", service)

    if search_service_module.jieba is not None:
        monkeypatch.setattr(
            search_service_module.jieba,
            "cut_for_search",
            lambda text: (text or "").split(),
        )

    return service


@pytest.mark.asyncio
async def test_create_folder(test_db):
    async with test_db() as session:
        service = FolderService(session)
        folder = await service.create_folder("Root")

        assert folder.id is not None
        assert folder.name == "Root"
        assert folder.parent_id is None


@pytest.mark.asyncio
async def test_create_nested_folder(test_db):
    async with test_db() as session:
        service = FolderService(session)
        parent = await service.create_folder("Parent")
        child = await service.create_folder("Child", parent_id=parent.id)

        assert child.id is not None
        assert child.parent_id == parent.id


@pytest.mark.asyncio
async def test_max_depth_exceeded(test_db):
    async with test_db() as session:
        service = FolderService(session)

        parent_id = None
        for depth in range(1, MAX_FOLDER_DEPTH + 1):
            folder = await service.create_folder(f"Level {depth}", parent_id=parent_id)
            parent_id = folder.id

        with pytest.raises(ValueError, match=r"Maximum folder depth"):
            await service.create_folder("Too deep", parent_id=parent_id)


@pytest.mark.asyncio
async def test_get_folder(test_db):
    async with test_db() as session:
        service = FolderService(session)
        created = await service.create_folder("Lookup")

        folder = await service.get_folder(created.id)
        assert folder is not None
        assert folder.id == created.id
        assert folder.name == "Lookup"


@pytest.mark.asyncio
async def test_update_folder(test_db):
    async with test_db() as session:
        service = FolderService(session)
        created = await service.create_folder("Old name")

        updated = await service.update_folder(created.id, "New name")
        assert updated is not None
        assert updated.id == created.id
        assert updated.name == "New name"


@pytest.mark.asyncio
async def test_update_folder_not_found(test_db):
    async with test_db() as session:
        service = FolderService(session)
        assert await service.update_folder(999999, "New name") is None


@pytest.mark.asyncio
async def test_delete_folder(test_db):
    async with test_db() as session:
        service = FolderService(session)
        folder = await service.create_folder("Delete me")

        assert await service.delete_folder(folder.id) is True
        assert await service.get_folder(folder.id) is None


@pytest.mark.asyncio
async def test_delete_folder_not_found(test_db):
    async with test_db() as session:
        service = FolderService(session)
        assert await service.delete_folder(999999) is False


@pytest.mark.asyncio
async def test_delete_folder_moves_documents(test_db):
    async with test_db() as session:
        service = FolderService(session)
        folder = await service.create_folder("Has docs")

        document = Document(
            filename="doc.md",
            original_name="doc.md",
            file_type="md",
            file_size=3,
            folder_id=folder.id,
        )
        session.add(document)
        await session.commit()
        await session.refresh(document)

        folder_id = folder.id
        document_id = document.id

        assert await service.delete_folder(folder_id) is True

    async with test_db() as session:
        moved = await session.get(Document, document_id)
        assert moved is not None
        assert moved.folder_id is None


@pytest.mark.asyncio
async def test_delete_folder_moves_children(test_db):
    async with test_db() as session:
        service = FolderService(session)
        root = await service.create_folder("Root")
        parent = await service.create_folder("Parent", parent_id=root.id)
        child = await service.create_folder("Child", parent_id=parent.id)

        root_id = root.id
        parent_id = parent.id
        child_id = child.id

        assert await service.delete_folder(parent_id) is True

    async with test_db() as session:
        service = FolderService(session)
        moved_child = await service.get_folder(child_id)
        assert moved_child is not None
        assert moved_child.parent_id == root_id
        assert await service.get_folder(parent_id) is None


@pytest.mark.asyncio
async def test_get_folder_tree(test_db):
    async with test_db() as session:
        service = FolderService(session)
        root = await service.create_folder("Projects")
        child_a = await service.create_folder("A", parent_id=root.id)
        child_b = await service.create_folder("B", parent_id=root.id)
        grandchild = await service.create_folder("A-1", parent_id=child_a.id)

        tree = await service.get_folder_tree()
        assert isinstance(tree, list)

        projects = next(node for node in tree if node["id"] == root.id)
        assert projects["parent_id"] is None

        children = {node["id"]: node for node in projects["children"]}
        assert set(children) == {child_a.id, child_b.id}
        assert children[child_a.id]["children"][0]["id"] == grandchild.id


@pytest.mark.asyncio
async def test_create_folder_api(client: AsyncClient):
    response = await client.post("/api/folders", json={"name": "API Root", "parent_id": None})
    assert response.status_code == 201

    payload = response.json()
    assert isinstance(payload["id"], int)
    assert payload["name"] == "API Root"
    assert payload["parent_id"] is None
    assert payload["created_at"]


@pytest.mark.asyncio
async def test_get_folder_tree_api(client: AsyncClient):
    root = await client.post("/api/folders", json={"name": "Root", "parent_id": None})
    root_id = root.json()["id"]

    child = await client.post("/api/folders", json={"name": "Child", "parent_id": root_id})
    child_id = child.json()["id"]

    response = await client.get("/api/folders")
    assert response.status_code == 200
    tree = response.json()

    root_node = next(node for node in tree if node["id"] == root_id)
    assert root_node["parent_id"] is None
    assert [n["id"] for n in root_node["children"]] == [child_id]


@pytest.mark.asyncio
async def test_get_folder_api(client: AsyncClient):
    created = await client.post("/api/folders", json={"name": "Get me", "parent_id": None})
    folder_id = created.json()["id"]

    response = await client.get(f"/api/folders/{folder_id}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == folder_id
    assert payload["name"] == "Get me"


@pytest.mark.asyncio
async def test_update_folder_api(client: AsyncClient):
    created = await client.post("/api/folders", json={"name": "Old", "parent_id": None})
    folder_id = created.json()["id"]

    response = await client.put(f"/api/folders/{folder_id}", json={"name": "Renamed"})
    assert response.status_code == 200
    assert response.json()["name"] == "Renamed"


@pytest.mark.asyncio
async def test_delete_folder_api(client: AsyncClient):
    created = await client.post("/api/folders", json={"name": "Delete", "parent_id": None})
    folder_id = created.json()["id"]

    response = await client.delete(f"/api/folders/{folder_id}")
    assert response.status_code == 200
    assert response.json() == {"message": "Folder deleted"}

    response = await client.get(f"/api/folders/{folder_id}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Folder not found"


@pytest.mark.asyncio
async def test_get_folder_api_not_found(client: AsyncClient):
    response = await client.get("/api/folders/999999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Folder not found"


@pytest.mark.asyncio
async def test_update_folder_api_not_found(client: AsyncClient):
    response = await client.put("/api/folders/999999", json={"name": "Renamed"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Folder not found"


@pytest.mark.asyncio
async def test_delete_folder_api_not_found(client: AsyncClient):
    response = await client.delete("/api/folders/999999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Folder not found"


@pytest.mark.asyncio
async def test_create_folder_depth_exceeded(client: AsyncClient):
    parent_id = None
    for depth in range(1, MAX_FOLDER_DEPTH + 1):
        response = await client.post(
            "/api/folders",
            json={"name": f"Depth {depth}", "parent_id": parent_id},
        )
        assert response.status_code == 201
        parent_id = response.json()["id"]

    response = await client.post(
        "/api/folders",
        json={"name": "Too deep", "parent_id": parent_id},
    )
    assert response.status_code == 400
    assert "Maximum folder depth" in response.json()["detail"]


@pytest.mark.asyncio
async def test_move_document(client: AsyncClient, test_db):
    async with test_db() as session:
        document = Document(
            filename="move.md",
            original_name="move.md",
            file_type="md",
            file_size=4,
            folder_id=None,
        )
        folder = Folder(name="Destination")
        session.add_all([document, folder])
        await session.commit()
        await session.refresh(document)
        await session.refresh(folder)

        doc_id = document.id
        folder_id = folder.id

    response = await client.post(
        f"/api/documents/{doc_id}/move",
        json={"folder_id": folder_id},
    )
    assert response.status_code == 200
    assert response.json()["id"] == doc_id
    assert response.json()["folder_id"] == folder_id

    response = await client.post(
        f"/api/documents/{doc_id}/move",
        json={"folder_id": None},
    )
    assert response.status_code == 200
    assert response.json()["folder_id"] is None

    async with test_db() as session:
        moved = await session.get(Document, doc_id)
        assert moved is not None
        assert moved.folder_id is None


@pytest.mark.asyncio
async def test_move_document_not_found(client: AsyncClient):
    response = await client.post("/api/documents/999999/move", json={"folder_id": None})
    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found"


@pytest.mark.asyncio
async def test_move_document_invalid_folder(client: AsyncClient, test_db):
    async with test_db() as session:
        document = Document(
            filename="move-bad.md",
            original_name="move-bad.md",
            file_type="md",
            file_size=8,
            folder_id=None,
        )
        session.add(document)
        await session.commit()
        await session.refresh(document)
        doc_id = document.id

    response = await client.post(
        f"/api/documents/{doc_id}/move",
        json={"folder_id": 999999},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Target folder not found"


@pytest.mark.asyncio
async def test_health_endpoints(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_get_db_yields_session(monkeypatch: pytest.MonkeyPatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        session_local = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        monkeypatch.setattr(database_module, "AsyncSessionLocal", session_local)

        gen = database_module.get_db()
        session = await gen.__anext__()
        assert isinstance(session, AsyncSession)
        await gen.aclose()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_lifespan_creates_upload_dir_and_inits_db(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    upload_dir = tmp_path / "uploads"
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(upload_dir))

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        session_local = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        monkeypatch.setattr(database_module, "async_engine", engine)
        monkeypatch.setattr(database_module, "AsyncSessionLocal", session_local)

        async with lifespan(app):
            assert upload_dir.is_dir()
    finally:
        await engine.dispose()


def test_parse_markdown(tmp_path: Path):
    path = tmp_path / "sample.md"
    path.write_text("# Title\n\nHello", encoding="utf-8")

    text, is_encrypted = DocumentParser.parse(path, "md")
    assert text == "# Title\n\nHello"
    assert is_encrypted is False


def test_parse_pdf(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake")

    monkeypatch.setattr(parser_module, "pypdf", None)
    text, is_encrypted = DocumentParser.parse(pdf_path, "pdf")
    assert text == ""
    assert is_encrypted is False

    class DummyEncryptedReader:
        def __init__(self, _path: str):
            self.is_encrypted = True
            self.pages = []

    class DummyPdfEncryptedModule:
        PdfReader = DummyEncryptedReader

    monkeypatch.setattr(parser_module, "pypdf", DummyPdfEncryptedModule)
    text, is_encrypted = DocumentParser.parse(pdf_path, "PDF")
    assert text == ""
    assert is_encrypted is True

    class DummyPage:
        def __init__(self, text):
            self._text = text

        def extract_text(self):
            return self._text

    class DummyReader:
        def __init__(self, _path: str):
            self.is_encrypted = False
            self.pages = [DummyPage("Hello "), DummyPage(None), DummyPage("World")]

    class DummyPdfModule:
        PdfReader = DummyReader

    monkeypatch.setattr(parser_module, "pypdf", DummyPdfModule)
    text, is_encrypted = DocumentParser.parse(pdf_path, "pdf")
    assert text == "Hello World"
    assert is_encrypted is False


def test_parse_docx(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    docx_path = tmp_path / "sample.docx"
    docx_path.write_bytes(b"fake docx")

    monkeypatch.setattr(parser_module, "DocxDocument", None)
    text, is_encrypted = DocumentParser.parse(docx_path, "docx")
    assert text == ""
    assert is_encrypted is False

    class DummyParagraph:
        def __init__(self, text: str):
            self.text = text

    class DummyDoc:
        def __init__(self, _path: str):
            self.paragraphs = [DummyParagraph("Line 1"), DummyParagraph("Line 2")]

    def dummy_docx_document(path: str):
        return DummyDoc(path)

    monkeypatch.setattr(parser_module, "DocxDocument", dummy_docx_document)
    text, is_encrypted = DocumentParser.parse(docx_path, "DOC")
    assert text == "Line 1\nLine 2"
    assert is_encrypted is False


def test_parse_excel(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    xlsx_path = tmp_path / "sample.xlsx"
    xlsx_path.write_bytes(b"fake xlsx")

    monkeypatch.setattr(parser_module, "load_workbook", None)
    text, is_encrypted = DocumentParser.parse(xlsx_path, "xlsx")
    assert text == ""
    assert is_encrypted is False

    class DummySheet:
        def __init__(self, rows):
            self._rows = rows

        def iter_rows(self, values_only: bool = False):
            assert values_only is True
            return self._rows

    class DummyWorkbook:
        def __init__(self, worksheets):
            self.worksheets = worksheets

    def dummy_load_workbook(path: str, *, read_only: bool, data_only: bool):
        assert path == str(xlsx_path)
        assert read_only is True
        assert data_only is True
        return DummyWorkbook(
            worksheets=[
                DummySheet(rows=[(1, None, "A"), (None, None), (" ",)]),
                DummySheet(rows=[("B",), (None, "C")]),
            ]
        )

    monkeypatch.setattr(parser_module, "load_workbook", dummy_load_workbook)
    text, is_encrypted = DocumentParser.parse(xlsx_path, "XLS")
    assert text == "1 A\nB\nC"
    assert is_encrypted is False


@pytest.mark.parametrize(
    ("file_type", "expected"),
    [
        ("pdf", True),
        ("PDF", True),
        ("docx", True),
        ("xlsx", True),
        ("md", True),
        ("exe", False),
    ],
)
def test_is_supported(file_type: str, expected: bool):
    assert DocumentParser.is_supported(file_type) is expected


@pytest.mark.parametrize(
    ("filename", "expected"),
    [("file.PDF", "pdf"), ("archive.tar.gz", "gz"), ("noext", "")],
)
def test_get_file_type(filename: str, expected: str):
    assert DocumentParser.get_file_type(filename) == expected


def test_parse_error_returns_empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    path = tmp_path / "sample.txt"
    path.write_text("Hello", encoding="utf-8")

    text, is_encrypted = DocumentParser.parse(path, "txt")
    assert text == ""
    assert is_encrypted is False

    def boom(_path: Path):
        raise RuntimeError("boom")

    monkeypatch.setattr(DocumentParser, "_parse_markdown", boom)
    md_path = tmp_path / "boom.md"
    md_path.write_text("Will error", encoding="utf-8")
    text, is_encrypted = DocumentParser.parse(md_path, "md")
    assert text == ""
    assert is_encrypted is False


@pytest.mark.asyncio
async def test_upload_document(
    client: AsyncClient,
    test_db,
    upload_dir: Path,
    inline_to_thread,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(document_service_module, "get_search_service", None)

    response = await client.post(
        "/api/documents/upload",
        files={"file": ("nested/hello.md", b"Hello", "text/markdown")},
    )
    assert response.status_code == 200

    payload = response.json()
    assert isinstance(payload["id"], int)
    assert payload["filename"].endswith(".md")
    assert payload["original_name"] == "hello.md"
    assert payload["file_type"] == "md"
    assert payload["file_size"] == 5
    assert payload["folder_id"] is None
    assert payload["created_at"]

    stored_path = upload_dir / payload["filename"]
    assert stored_path.is_file()
    assert stored_path.read_bytes() == b"Hello"

    async with test_db() as session:
        doc = await session.get(Document, payload["id"])
        assert doc is not None
        assert doc.content_text == "Hello"


@pytest.mark.asyncio
async def test_upload_document_missing_filename_returns_400(test_db):
    class DummyUpload:
        filename = ""

    async with test_db() as session:
        with pytest.raises(HTTPException) as exc:
            await documents_router.upload_document(
                file=DummyUpload(),
                folder_id=None,
                db=session,
            )

    assert exc.value.status_code == 400
    assert exc.value.detail == "Missing filename"


@pytest.mark.asyncio
async def test_upload_unsupported_type(client: AsyncClient):
    response = await client.post(
        "/api/documents/upload",
        files={"file": ("malware.exe", b"nope", "application/octet-stream")},
    )
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_file_too_large(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
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
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(document_service_module, "get_search_service", None)

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
async def test_get_document_endpoint(
    client: AsyncClient,
    upload_dir: Path,
    inline_to_thread,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(document_service_module, "get_search_service", None)

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
async def test_delete_document_endpoint(
    client: AsyncClient,
    upload_dir: Path,
    inline_to_thread,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(document_service_module, "get_search_service", None)

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

    class ExplodingSearchService:
        def index_document(self, *args, **kwargs):
            raise RuntimeError("boom")

        def remove_document(self, *args, **kwargs):
            raise RuntimeError("boom")

    monkeypatch.setattr(document_service_module.DocumentParser, "parse", dummy_parse)
    monkeypatch.setattr(
        document_service_module, "get_search_service", lambda: ExplodingSearchService()
    )

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

    DocumentService._safe_delete_file(MissingPath())

    class ExplodingPath:
        def unlink(self):
            raise RuntimeError("boom")

    DocumentService._safe_delete_file(ExplodingPath())


def test_search_service_highlight_variants(search_service: SearchService, monkeypatch: pytest.MonkeyPatch):
    assert search_service.highlight("", "q") == ""
    assert search_service.highlight("content", "") == "content"
    assert search_service.highlight("hello", "zzz") == "hello"

    monkeypatch.setattr(search_service_module, "jieba", None)
    assert search_service.highlight("x" * 250, "q").endswith("...")


def test_jieba_tokenizer_skips_blank_tokens(monkeypatch: pytest.MonkeyPatch):
    if not hasattr(search_service_module, "JiebaTokenizer"):
        pytest.skip("Search backend not available")

    monkeypatch.setattr(
        search_service_module.jieba,
        "cut_for_search",
        lambda _text: [" ", "hello"],
    )

    tokenizer = search_service_module.JiebaTokenizer()
    tokens = list(tokenizer("ignored"))
    assert [token.text for token in tokens] == ["hello"]


def test_search_service_backend_disabled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(search_service_module, "_SEARCH_BACKEND_AVAILABLE", False)
    monkeypatch.setattr(search_service_module, "SCHEMA", None)

    service = SearchService(index_dir=str(tmp_path / "idx"))
    with pytest.raises(RuntimeError):
        service._require_backend()

    service.index_document(
        doc_id=1,
        content="hello",
        file_type="md",
        folder_id=None,
        tag_ids=[],
        created_at=datetime.utcnow(),
    )
    service.remove_document(1)


@pytest.mark.asyncio
async def test_search_service_search_and_remove(search_service: SearchService):
    now = datetime.utcnow()
    search_service.index_document(
        doc_id=1,
        content="hello world",
        file_type="md",
        folder_id=10,
        tag_ids=[1],
        created_at=now,
    )
    search_service.index_document(
        doc_id=2,
        content="hello again",
        file_type="pdf",
        folder_id=None,
        tag_ids=[2],
        created_at=now - timedelta(days=2),
    )

    search_service._ix = None
    _ = search_service.ix

    items, total = search_service.search(
        query="hello",
        file_type="md",
        folder_id=10,
        tag_ids=[1],
        date_from=now - timedelta(days=1),
        date_to=now + timedelta(days=1),
    )
    assert total == 1
    assert items[0]["doc_id"] == 1
    assert "<mark>" in items[0]["highlight"]

    _items, total = search_service.search(query="hello", tag_ids=[999])
    assert total == 0

    _items, total = search_service.search(query="hello", date_from=now + timedelta(days=1))
    assert total == 0

    _items, total = search_service.search(query="hello", date_to=now - timedelta(days=3))
    assert total == 0

    search_service.remove_document(1)


@pytest.mark.asyncio
async def test_search_api(client: AsyncClient, search_service: SearchService):
    now = datetime.utcnow()
    search_service.index_document(
        doc_id=123,
        content="hello folder",
        file_type="md",
        folder_id=5,
        tag_ids=[7],
        created_at=now,
    )

    response = await client.get(
        "/api/search",
        params={"q": "hello", "type": "md", "folder_id": 5, "tag_ids": "7"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["doc_id"] == 123
    assert payload["took_ms"] >= 0


@pytest.mark.asyncio
async def test_search_api_invalid_tag_ids_returns_400(client: AsyncClient):
    response = await client.get("/api/search", params={"q": "hello", "tag_ids": "1,a"})
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid tag_ids format"


@pytest.mark.asyncio
async def test_search_api_backend_error_returns_503(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    class ExplodingSearchService:
        def search(self, *args, **kwargs):
            raise RuntimeError("boom")

    monkeypatch.setattr(search_router, "get_search_service", lambda: ExplodingSearchService())
    response = await client.get("/api/search", params={"q": "hello"})
    assert response.status_code == 503
    assert "boom" in response.json()["detail"]
