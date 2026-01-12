from __future__ import annotations

from pathlib import Path
from typing import Optional

import pytest

import app.services.parser as parser_module
from app.services.parser import DocumentParser


@pytest.fixture
def markdown_file(tmp_path: Path) -> Path:
    path = tmp_path / "sample.md"
    path.write_text("# Title\n\nHello", encoding="utf-8")
    return path


def test_parse_markdown(markdown_file: Path):
    text, is_encrypted = DocumentParser.parse(markdown_file, "md")
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
        def __init__(self, text: Optional[str]):
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
    [("pdf", True), ("PDF", True), ("docx", True), ("xlsx", True), ("md", True), ("exe", False)],
)
def test_is_supported(file_type: str, expected: bool):
    assert DocumentParser.is_supported(file_type) is expected


@pytest.mark.parametrize(
    ("filename", "expected"),
    [("file.PDF", "pdf"), ("archive.tar.gz", "gz"), ("noext", "")],
)
def test_get_file_type(filename: str, expected: str):
    assert DocumentParser.get_file_type(filename) == expected


def test_unsupported_type(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
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
