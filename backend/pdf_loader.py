"""Reads PDFs page by page and splits pages into overlapping, sentence-aware chunks."""
import re
from pypdf import PdfReader
from config import CHUNK_SIZE, CHUNK_OVERLAP


def clean(text: str) -> str:
    text = re.sub(r"-\n(\w)", r"\1", text)        # re-join hyphenated line breaks
    text = re.sub(r"[ \t\u00a0]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?;])\s+|\n+", text)
    return [p.strip() for p in parts if p and p.strip()]


def load_pdf(path) -> list[tuple[int, str]]:
    """Returns [(page_number starting at 1, text)] for pages that contain text."""
    reader = PdfReader(str(path))
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        try:
            text = clean(page.extract_text() or "")
        except Exception:
            text = ""
        if text:
            pages.append((i, text))
    return pages


def read_page(path, page: int) -> str:
    reader = PdfReader(str(path))
    if page < 1 or page > len(reader.pages):
        raise IndexError("page out of range")
    return clean(reader.pages[page - 1].extract_text() or "")


def chunk_page(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    # hard-split any single sentence that is longer than a chunk
    sentences = []
    for s in split_sentences(text):
        while len(s) > size:
            sentences.append(s[:size])
            s = s[size:]
        sentences.append(s)

    chunks, current = [], []
    length = 0
    for s in sentences:
        if current and length + len(s) + 1 > size:
            chunks.append(" ".join(current))
            # carry the tail of the previous chunk forward as overlap
            tail, tail_len = [], 0
            for prev in reversed(current):
                if tail_len + len(prev) > overlap:
                    break
                tail.insert(0, prev)
                tail_len += len(prev) + 1
            current, length = tail, tail_len
        current.append(s)
        length += len(s) + 1
    if current:
        last = " ".join(current)
        if not chunks or last != chunks[-1]:
            chunks.append(last)
    return chunks


def build_chunks(file_name: str, pages: list[tuple[int, str]]) -> list[dict]:
    out = []
    for page_no, text in pages:
        for j, piece in enumerate(chunk_page(text)):
            out.append({
                "id": f"{file_name}::p{page_no}::c{j}",
                "file": file_name,
                "page": page_no,
                "chunk": j,
                "text": piece,
            })
    return out