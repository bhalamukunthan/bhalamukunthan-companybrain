"""Split text into chunks of roughly `size` characters, keeping paragraphs together."""
import re


def _split_long(paragraph: str, size: int, overlap: int) -> list[str]:
    out, start = [], 0
    while start < len(paragraph):
        out.append(paragraph[start:start + size])
        if start + size >= len(paragraph):
            break
        start += size - overlap
    return out


def chunk_text(text: str, size: int = 800, overlap: int = 100) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    pieces: list[str] = []
    for p in paragraphs:
        pieces.extend(_split_long(p, size, overlap) if len(p) > size else [p])
    chunks, current = [], ""
    for piece in pieces:
        if current and len(current) + len(piece) + 2 > size:
            chunks.append(current)
            current = piece
        else:
            current = f"{current}\n\n{piece}" if current else piece
    if current:
        chunks.append(current)
    return chunks
