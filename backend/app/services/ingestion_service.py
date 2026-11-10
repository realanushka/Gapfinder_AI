"""Upload -> extract -> detect structure -> chunk -> embed (Plan Step 3)."""

import io
import re
from dataclasses import dataclass

try:
    import fitz  # PyMuPDF: fast, preferred
except ImportError:  # e.g. a missing Windows C++ runtime -> DLL load failure
    fitz = None

CHAPTER_PATTERN = re.compile(r"^\s*chapter\s+\d+", re.IGNORECASE)
SECTION_PATTERN = re.compile(r"^\s*\d+\.\d+\s")

CHUNK_WORD_SIZE = 400
CHUNK_WORD_OVERLAP = 50


@dataclass
class PageText:
    page: int
    text: str


@dataclass
class ChunkDraft:
    text: str
    chapter: str | None
    section: str | None
    page: int


def _is_pdf(file_bytes: bytes, filename: str) -> bool:
    """A file is a PDF if it says so by name or by its header.

    Going by the name matters: a corrupt "report.pdf" must be rejected, not
    quietly ingested as plain text.
    """
    return filename.lower().endswith(".pdf") or file_bytes.lstrip().startswith(b"%PDF")


def extract_pages(file_bytes: bytes, filename: str = "") -> list[PageText]:
    """Extract text per page, using PyMuPDF if it loads and pdfplumber otherwise.

    Plain-text files (the Upload page accepts .txt) have no real pages, so they
    become page 1. Form-feed characters, if present, mark page breaks.
    Raises ValueError for content that is neither a readable PDF nor text.
    """
    pages: list[PageText] = []
    if not _is_pdf(file_bytes, filename):
        if b"\x00" in file_bytes[:2048]:
            raise ValueError("This looks like a binary file, not text.")
        text = file_bytes.decode("utf-8", errors="replace")
        return [
            PageText(page=number, text=part)
            for number, part in enumerate(text.split("\f"), start=1)
        ]
    if fitz is not None:
        with fitz.open(stream=file_bytes, filetype="pdf") as doc:
            for page_number, page in enumerate(doc, start=1):
                pages.append(PageText(page=page_number, text=page.get_text()))
        return pages

    import pdfplumber

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            pages.append(PageText(page=page_number, text=page.extract_text() or ""))
    return pages


def detect_structure(pages: list[PageText]) -> list[ChunkDraft]:
    """Walk pages line by line, tracking the most recent chapter/section heading."""
    current_chapter: str | None = None
    current_section: str | None = None
    drafts: list[ChunkDraft] = []

    for page in pages:
        for line in page.text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if CHAPTER_PATTERN.match(stripped):
                current_chapter = stripped
                continue
            if SECTION_PATTERN.match(stripped):
                current_section = stripped
                continue
            drafts.append(
                ChunkDraft(
                    text=stripped,
                    chapter=current_chapter,
                    section=current_section,
                    page=page.page,
                )
            )
    return drafts


def chunk_text(drafts: list[ChunkDraft]) -> list[ChunkDraft]:
    """Merge line-level drafts into ~400-word chunks with a small overlap."""
    chunks: list[ChunkDraft] = []
    buffer_words: list[str] = []
    buffer_chapter: str | None = None
    buffer_section: str | None = None
    buffer_page: int | None = None

    def flush() -> None:
        if buffer_words:
            chunks.append(
                ChunkDraft(
                    text=" ".join(buffer_words),
                    chapter=buffer_chapter,
                    section=buffer_section,
                    page=buffer_page or 1,
                )
            )

    for draft in drafts:
        # A new chapter/section heading always starts a fresh chunk, so a chunk
        # never straddles two sections and its citation stays accurate.
        if buffer_words and (
            draft.chapter != buffer_chapter or draft.section != buffer_section
        ):
            flush()
            buffer_words = []
            buffer_chapter, buffer_section, buffer_page = (
                draft.chapter,
                draft.section,
                draft.page,
            )

        if buffer_page is None:
            buffer_chapter, buffer_section, buffer_page = (
                draft.chapter,
                draft.section,
                draft.page,
            )

        words = draft.text.split()
        buffer_words.extend(words)

        if len(buffer_words) >= CHUNK_WORD_SIZE:
            flush()
            buffer_words = buffer_words[-CHUNK_WORD_OVERLAP:]
            buffer_chapter, buffer_section, buffer_page = (
                draft.chapter,
                draft.section,
                draft.page,
            )

    flush()
    return chunks
