"""Page-aware chunking.

Rules:
- Split each page into paragraphs (blank lines, or numbered clauses like "2.1 ...").
- Merge paragraphs into chunks of about `size` words, carrying `overlap` words forward.
- A chunk NEVER crosses a page boundary, so each chunk has exactly one page number.
- Skip chunks that are too short or that are mostly non-letters (page numbers, rules, headers).
"""
import re
from dataclasses import dataclass

PARA_SPLIT = re.compile(r"\n\s*\n|\n(?=\d+(?:\.\d+)+\s)")
MIN_WORDS = 8


@dataclass
class TextChunk:
    page: int
    text: str


def _split_paragraphs(text: str) -> list[str]:
    return [" ".join(p.split()) for p in PARA_SPLIT.split(text) if p.strip()]


def chunk_page(text: str, size: int, overlap: int) -> list[str]:
    """Split one page of text into overlapping word chunks."""
    overlap = max(0, min(overlap, size // 2))
    chunks: list[str] = []
    cur: list[str] = []
    fresh = 0  # words in `cur` that are new (not carried over as overlap)

    def close() -> None:
        nonlocal cur, fresh
        chunks.append(" ".join(cur))
        cur = cur[-overlap:] if overlap else []
        fresh = 0

    for para in _split_paragraphs(text):
        words = para.split(" ")
        if cur and fresh > 0 and len(cur) + len(words) > size:
            close()
        for word in words:
            cur.append(word)
            fresh += 1
            if len(cur) >= size:
                close()
    if fresh > 0:
        chunks.append(" ".join(cur))
    return chunks


def _is_useful(text: str) -> bool:
    if len(text.split()) < MIN_WORDS:
        return False
    letters = sum(c.isalpha() for c in text)
    return letters / max(len(text), 1) >= 0.5


def chunk_pages(pages: list[tuple[int, str]], size: int, overlap: int) -> list[TextChunk]:
    """Chunk a whole document. `pages` is a list of (page_number, text)."""
    out: list[TextChunk] = []
    for page_no, text in pages:
        for piece in chunk_page(text, size, overlap):
            if _is_useful(piece):
                out.append(TextChunk(page=page_no, text=piece))
    return out
