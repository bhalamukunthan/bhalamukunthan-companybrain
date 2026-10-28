"""Turn uploaded bytes into text pages. Rejects bad files with a clear message."""
from pathlib import Path

import fitz  # PyMuPDF


class ParseError(Exception):
    pass


def extract_pages(filename: str, data: bytes) -> list[tuple[int | None, str]]:
    """Returns [(page_number_or_None, text), ...] with empty pages removed."""
    ext = Path(filename).suffix.lower()
    if not data:
        raise ParseError("The file is empty")
    if ext == ".txt":
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise ParseError("TXT file must be UTF-8 text")
        pages = [(None, text)]
    elif ext == ".pdf":
        if not data.startswith(b"%PDF"):
            raise ParseError("File is not a valid PDF")
        try:
            doc = fitz.open(stream=data, filetype="pdf")
            if doc.needs_pass:
                raise ParseError("Password-protected PDFs are not supported")
            pages = [(i + 1, page.get_text()) for i, page in enumerate(doc)]
        except ParseError:
            raise
        except Exception:
            raise ParseError("The PDF is corrupted or unreadable")
    else:
        raise ParseError("Only .pdf and .txt files are supported")
    pages = [(n, t) for n, t in pages if t.strip()]
    if not pages:
        raise ParseError("No readable text found (scanned/image-only PDFs are not supported)")
    return pages
