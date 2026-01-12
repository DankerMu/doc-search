from __future__ import annotations

import io
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from starlette.datastructures import UploadFile

import app.routers.documents as documents_router
import app.services.document_service as document_service_module
import app.services.parser as parser_module
import app.services.search_service as search_service_module
from app.core.config import settings
from app.core.database import get_db
from app.main import app, lifespan
from app.services.document_service import DocumentService
from app.services.parser import DocumentParser
from app.services.search_service import SearchService


class _StubJieba:
    @staticmethod
    def cut_for_search(text: str):
        text = (text or "").strip()
        if not text:
            return []
        parts = [part for part in text.split() if part]
        return parts or [text]


class _FakeHit(dict):
    def __init__(self, fields: dict, score: float):
        super().__init__(fields)
        self.score = float(score)


class _FakeWriter:
    def __init__(self, store: dict[str, dict]):
        self._store = store

    def update_document(self, **fields):
        doc_id = fields["doc_id"]
        self._store[doc_id] = dict(fields)

    def delete_by_term(self, field: str, value: str):
        if field != "doc_id":
            return
        self._store.pop(value, None)

    def commit(self) -> None:
        return


class _FakeSearcher:
    def __init__(self, store: dict[str, dict]):
        self._store = store

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def search(self, query: str, limit: int = 20):
        tokens = list(_StubJieba.cut_for_search(str(query)))
        if not tokens:
            return []

        hits: list[_FakeHit] = []
        for doc in self._store.values():
            content = str(doc.get("content") or "")
            content_lower = content.lower()
            if not all(token.lower() in content_lower for token in tokens):
                continue
            score = sum(content_lower.count(token.lower()) for token in tokens)
            hits.append(_FakeHit(doc, score=score))

        hits.sort(key=lambda hit: hit.score, reverse=True)
        return hits[:limit]


class _FakeIndex:
    def __init__(self, schema):
        self.schema = schema
        self._store: dict[str, dict] = {}

    def writer(self):
        return _FakeWriter(self._store)

    def searcher(self, weighting=None):
        return _FakeSearcher(self._store)


class _FakeIndexModule:
    def __init__(self):
        self._indexes: dict[str, _FakeIndex] = {}

    def exists_in(self, directory: str) -> bool:
        return directory in self._indexes

    def open_dir(self, directory: str):
        return self._indexes[directory]

    def create_in(self, directory: str, schema):
        ix = _FakeIndex(schema=schema)
        self._indexes[directory] = ix
        return ix


class _FakeMultifieldParser:
    def __init__(self, fields, schema):
        self.fields = fields
        self.schema = schema

    def parse(self, query: str):
        return query


class _FakeQueryParser:
    def __init__(self, fieldname: str, schema):
        self.fieldname = fieldname
        self.schema = schema

    def parse(self, query: str):
        return query


class _FakeBM25F:
    def __init__(self, *args, **kwargs):
        return


@pytest.fixture(autouse=True)
def ensure_search_backend(monkeypatch: pytest.MonkeyPatch):
    if search_service_module._SEARCH_BACKEND_AVAILABLE:
        return

    fake_index = _FakeIndexModule()
    monkeypatch.setattr(search_service_module, "jieba", _StubJieba)
    monkeypatch.setattr(search_service_module, "index", fake_index)
    monkeypatch.setattr(search_service_module, "MultifieldParser", _FakeMultifieldParser)
    monkeypatch.setattr(search_service_module, "QueryParser", _FakeQueryParser)
    monkeypatch.setattr(search_service_module, "BM25F", _FakeBM25F)
    monkeypatch.setattr(search_service_module, "SCHEMA", object())
    monkeypatch.setattr(search_service_module, "_SEARCH_BACKEND_AVAILABLE", True)


@pytest.fixture
def index_dir(tmp_path: Path) -> Path:
    return tmp_path / "search_index"


@pytest.fixture
def search_service(index_dir: Path, monkeypatch: pytest.MonkeyPatch) -> SearchService:
    service = SearchService(index_dir=str(index_dir))
    monkeypatch.setattr(search_service_module, "_search_service", service)
    return service


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


def _index_document(
    service: SearchService,
    *,
    doc_id: int,
    content: str,
    file_type: str = "md",
    folder_id: int | None = None,
    tag_ids: list[int] | None = None,
    created_at: datetime | None = None,
) -> None:
    service.index_document(
        doc_id=doc_id,
        content=content,
        file_type=file_type,
        folder_id=folder_id,
        tag_ids=tag_ids or [],
        created_at=created_at or datetime.utcnow(),
    )


def test_index_and_search(search_service: SearchService):
    _index_document(
        search_service,
        doc_id=1,
        content="hello world",
        file_type="md",
        folder_id=None,
        tag_ids=[],
    )

    items, total = search_service.search("hello")
    assert total == 1
    assert [item["doc_id"] for item in items] == [1]


def test_remove_document(search_service: SearchService):
    _index_document(search_service, doc_id=1, content="remove me")
    items, total = search_service.search("remove")
    assert total == 1
    assert [item["doc_id"] for item in items] == [1]

    search_service.remove_document(1)
    items, total = search_service.search("remove")
    assert total == 0
    assert items == []


def test_chinese_search(search_service: SearchService):
    _index_document(
        search_service,
        doc_id=1,
        content="我喜欢自然语言处理和机器学习",
        file_type="txt",
    )

    items, total = search_service.search("自然语言处理")
    assert total == 1
    assert items[0]["doc_id"] == 1


def test_highlight(search_service: SearchService):
    content = "prefix " + ("x " * 50) + "hello" + (" y" * 50) + " suffix"
    highlighted = search_service.highlight(content, "hello")
    assert "<mark>hello</mark>" in highlighted


def test_filter_by_type(search_service: SearchService):
    _index_document(
        search_service,
        doc_id=1,
        content="hello world",
        file_type="md",
    )
    _index_document(
        search_service,
        doc_id=2,
        content="hello world",
        file_type="pdf",
    )

    items, total = search_service.search("hello", file_type="pdf")
    assert total == 1
    assert [item["doc_id"] for item in items] == [2]
    assert items[0]["file_type"] == "pdf"


def test_filter_by_folder(search_service: SearchService):
    _index_document(
        search_service,
        doc_id=1,
        content="hello world",
        folder_id=1,
    )
    _index_document(
        search_service,
        doc_id=2,
        content="hello world",
        folder_id=2,
    )

    items, total = search_service.search("hello", folder_id=1)
    assert total == 1
    assert [item["doc_id"] for item in items] == [1]
    assert items[0]["folder_id"] == 1


def test_pagination(search_service: SearchService):
    for doc_id in range(1, 26):
        _index_document(
            search_service,
            doc_id=doc_id,
            content=("common " * doc_id).strip(),
        )

    all_items, total = search_service.search("common", skip=0, limit=100)
    page_items, page_total = search_service.search("common", skip=5, limit=5)

    assert total == 25
    assert page_total == 25
    assert len(page_items) == 5
    assert [item["doc_id"] for item in page_items] == [
        item["doc_id"] for item in all_items[5:10]
    ]


@pytest.mark.asyncio
async def test_search_endpoint(
    client: AsyncClient,
    search_service: SearchService,
    upload_dir: Path,
    inline_to_thread,
):
    upload = await client.post(
        "/api/documents/upload",
        files={"file": ("hello.md", b"hello search", "text/markdown")},
    )
    assert upload.status_code == 200
    doc_id = upload.json()["id"]

    response = await client.get("/api/search", params={"q": "hello"})
    assert response.status_code == 200

    payload = response.json()
    assert set(payload) == {"items", "total", "took_ms"}
    assert payload["total"] == 1
    assert isinstance(payload["took_ms"], int)
    assert payload["took_ms"] >= 0

    assert len(payload["items"]) == 1
    item = payload["items"][0]
    assert item["doc_id"] == doc_id
    assert item["file_type"] == "md"
    assert item["folder_id"] is None
    assert isinstance(item["score"], float)
    assert "<mark>hello</mark>" in item["highlight"]


@pytest.mark.asyncio
async def test_search_with_filters(client: AsyncClient, search_service: SearchService):
    now = datetime.utcnow()
    _index_document(
        search_service,
        doc_id=1,
        content="hello world",
        file_type="md",
        folder_id=1,
        tag_ids=[1, 2],
        created_at=now,
    )
    _index_document(
        search_service,
        doc_id=2,
        content="hello world",
        file_type="pdf",
        folder_id=1,
        tag_ids=[2],
        created_at=now,
    )
    _index_document(
        search_service,
        doc_id=3,
        content="hello world",
        file_type="md",
        folder_id=2,
        tag_ids=[3],
        created_at=now - timedelta(days=1),
    )

    response = await client.get(
        "/api/search",
        params={"q": "hello", "type": "md", "folder_id": 1, "tag_ids": "1"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert [item["doc_id"] for item in payload["items"]] == [1]


@pytest.mark.asyncio
async def test_search_empty_query(client: AsyncClient):
    response = await client.get("/api/search", params={"q": ""})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_search_performance(client: AsyncClient, search_service: SearchService):
    for doc_id in range(1, 51):
        _index_document(search_service, doc_id=doc_id, content="perf perf perf")

    await client.get("/api/search", params={"q": "perf"})  # warmup

    start = time.perf_counter()
    response = await client.get("/api/search", params={"q": "perf"})
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert response.status_code == 200
    assert elapsed_ms < 500


@pytest.mark.asyncio
async def test_health_endpoints(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "version": "1.0.0"}

    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "version": "1.0.0"}


@pytest.mark.asyncio
async def test_lifespan_creates_upload_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    upload_dir = tmp_path / "uploads"
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(upload_dir))

    async with lifespan(app):
        assert upload_dir.is_dir()


@pytest.mark.asyncio
async def test_get_db_yields_session():
    async for session in get_db():
        assert session is not None
        break


@pytest.mark.asyncio
async def test_search_invalid_tag_ids_returns_400(client: AsyncClient):
    response = await client.get("/api/search", params={"q": "hello", "tag_ids": "not-an-int"})
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_search_runtime_error_returns_503(
    client: AsyncClient, search_service: SearchService, monkeypatch: pytest.MonkeyPatch
):
    def boom(*_args, **_kwargs):
        raise RuntimeError("backend down")

    monkeypatch.setattr(search_service, "search", boom)
    response = await client.get("/api/search", params={"q": "hello"})
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_upload_missing_filename_returns_400(
    client: AsyncClient, search_service: SearchService
):
    response = await client.post(
        "/api/documents/upload",
        files={"file": ("", b"hello", "text/markdown")},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_documents_router_missing_filename_branch_returns_400(
    test_db,
    upload_dir: Path,
    inline_to_thread,
):
    async with test_db() as session:
        file = UploadFile(filename="", file=io.BytesIO(b"hello"))
        with pytest.raises(HTTPException) as exc:
            await documents_router.upload_document(file=file, folder_id=None, db=session)
        assert exc.value.status_code == 400
        assert exc.value.detail == "Missing filename"


@pytest.mark.asyncio
async def test_upload_unsupported_type_returns_400(
    client: AsyncClient, search_service: SearchService
):
    response = await client.post(
        "/api/documents/upload",
        files={"file": ("malware.exe", b"nope", "application/octet-stream")},
    )
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_file_too_large_returns_400(
    client: AsyncClient,
    search_service: SearchService,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(documents_router, "MAX_FILE_SIZE", 4)
    response = await client.post(
        "/api/documents/upload",
        files={"file": ("big.md", b"12345", "text/markdown")},
    )
    assert response.status_code == 400
    assert "File too large" in response.json()["detail"]


@pytest.mark.asyncio
async def test_list_get_and_delete_document(
    client: AsyncClient,
    search_service: SearchService,
    upload_dir: Path,
    inline_to_thread,
):
    upload_a = await client.post(
        "/api/documents/upload",
        files={"file": ("a.md", b"hello a", "text/markdown")},
    )
    assert upload_a.status_code == 200

    upload_b = await client.post(
        "/api/documents/upload",
        files={"file": ("b.md", b"hello b", "text/markdown")},
    )
    assert upload_b.status_code == 200

    list_response = await client.get("/api/documents")
    assert list_response.status_code == 200
    payload = list_response.json()
    assert payload["total"] == 2
    assert {item["original_name"] for item in payload["items"]} == {"a.md", "b.md"}

    doc_id = upload_a.json()["id"]
    get_response = await client.get(f"/api/documents/{doc_id}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == doc_id

    stored_filename = upload_a.json()["filename"]
    stored_path = upload_dir / stored_filename
    assert stored_path.exists() is True

    delete_response = await client.delete(f"/api/documents/{doc_id}")
    assert delete_response.status_code == 200
    assert delete_response.json() == {"message": "Document deleted"}
    assert stored_path.exists() is False


@pytest.mark.asyncio
async def test_get_document_not_found_returns_404(client: AsyncClient):
    response = await client.get("/api/documents/999999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found"


@pytest.mark.asyncio
async def test_delete_document_not_found_returns_404(client: AsyncClient):
    response = await client.delete("/api/documents/999999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found"


@pytest.mark.asyncio
async def test_documents_router_direct_calls(
    test_db,
    upload_dir: Path,
    inline_to_thread,
    search_service: SearchService,
):
    async with test_db() as session:
        uploaded = await documents_router.upload_document(
            file=UploadFile(filename="direct.md", file=io.BytesIO(b"hello direct")),
            folder_id=None,
            db=session,
        )
        assert uploaded.id is not None

        listed = await documents_router.list_documents(
            folder_id=None,
            skip=0,
            limit=20,
            db=session,
        )
        assert listed.total >= 1

        fetched = await documents_router.get_document(uploaded.id, db=session)
        assert fetched.id == uploaded.id

        with pytest.raises(HTTPException) as exc:
            await documents_router.get_document(999999, db=session)
        assert exc.value.status_code == 404

        deleted = await documents_router.delete_document(uploaded.id, db=session)
        assert deleted == {"message": "Document deleted"}

        with pytest.raises(HTTPException) as exc:
            await documents_router.delete_document(999999, db=session)
        assert exc.value.status_code == 404


def test_document_parser_markdown(tmp_path: Path):
    path = tmp_path / "sample.md"
    path.write_text("# Title\n\nHello", encoding="utf-8")
    text, is_encrypted = DocumentParser.parse(path, "md")
    assert text == "# Title\n\nHello"
    assert is_encrypted is False


def test_document_parser_unsupported_type_returns_empty(tmp_path: Path):
    path = tmp_path / "sample.txt"
    path.write_text("Hello", encoding="utf-8")
    text, is_encrypted = DocumentParser.parse(path, "txt")
    assert text == ""
    assert is_encrypted is False


def test_document_parser_pdf_docx_excel_and_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
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
        def __init__(self, page_text: str | None):
            self._text = page_text

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

    def boom(_path: Path):
        raise RuntimeError("boom")

    monkeypatch.setattr(DocumentParser, "_parse_markdown", boom)
    md_path = tmp_path / "boom.md"
    md_path.write_text("Will error", encoding="utf-8")
    text, is_encrypted = DocumentParser.parse(md_path, "md")
    assert text == ""
    assert is_encrypted is False


@pytest.mark.parametrize(
    ("file_type", "expected"),
    [("pdf", True), ("PDF", True), ("docx", True), ("xlsx", True), ("md", True), ("exe", False)],
)
def test_document_parser_is_supported(file_type: str, expected: bool):
    assert DocumentParser.is_supported(file_type) is expected


@pytest.mark.parametrize(
    ("filename", "expected"),
    [("file.PDF", "pdf"), ("archive.tar.gz", "gz"), ("noext", "")],
)
def test_document_parser_get_file_type(filename: str, expected: str):
    assert DocumentParser.get_file_type(filename) == expected


@pytest.mark.asyncio
async def test_document_service_list_documents_filters_folder(
    test_db, upload_dir: Path, inline_to_thread, search_service: SearchService
):
    async with test_db() as session:
        service = DocumentService(session)
        await service.save_document("one.md", b"One", "md", folder_id=1)
        await service.save_document("two.md", b"Two", "md", folder_id=None)

        items, total = await service.list_documents(folder_id=1, skip=0, limit=20)
        assert total == 1
        assert [doc.original_name for doc in items] == ["one.md"]


@pytest.mark.asyncio
async def test_document_service_delete_document_returns_false(test_db):
    async with test_db() as session:
        service = DocumentService(session)
        assert await service.delete_document(999999) is False


@pytest.mark.asyncio
async def test_document_service_delete_document_removes_file(
    test_db,
    upload_dir: Path,
    inline_to_thread,
    search_service: SearchService,
):
    async with test_db() as session:
        service = DocumentService(session)
        document = await service.save_document("del.md", b"Delete me", "md")

        stored_path = Path(settings.UPLOAD_DIR) / document.filename
        assert stored_path.exists() is True

        assert await service.delete_document(document.id) is True
        assert stored_path.exists() is False


@pytest.mark.asyncio
async def test_document_service_swallow_search_index_errors(
    test_db,
    upload_dir: Path,
    inline_to_thread,
    monkeypatch: pytest.MonkeyPatch,
):
    class ExplodingSearchService:
        def index_document(self, *args, **kwargs):
            raise RuntimeError("boom")

        def remove_document(self, *args, **kwargs):
            raise RuntimeError("boom")

    monkeypatch.setattr(document_service_module, "get_search_service", lambda: ExplodingSearchService())

    async with test_db() as session:
        service = DocumentService(session)
        document = await service.save_document("boom.md", b"Hello", "md")
        assert document.id is not None
        assert await service.delete_document(document.id) is True


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
