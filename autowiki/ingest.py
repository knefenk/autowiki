"""Document ingestion helpers  -  chunking, format detection, extraction."""

import re
from pathlib import Path
from typing import Iterator, Optional

# Approximate token count: ~4 chars per token for English text
CHARS_PER_TOKEN = 4
CHUNK_TARGET_TOKENS = 3000
CHUNK_TARGET_CHARS = CHUNK_TARGET_TOKENS * CHARS_PER_TOKEN  # ~12K chars


def detect_type(filepath: Path) -> str:
    """Detect document type from file extension.

    Returns one of: article, paper, code, log, data
    """
    ext = filepath.suffix.lower()
    if ext == ".pdf":
        return "paper"
    if ext in (".py", ".js", ".ts", ".go", ".rs", ".java", ".c", ".cpp", ".h"):
        return "code"
    if ext in (".jsonl", ".log", ".json"):
        return "log"
    if ext in (".csv", ".tsv"):
        return "data"
    return "article"


def chunk_text(text: str, target_chars: int = CHUNK_TARGET_CHARS) -> Iterator[str]:
    """Split text into chunks targeting ~target_chars each.

    Prefers splitting at section headers (## or #) and paragraph boundaries.
    Falls back to hard splits at target_chars.
    """
    if len(text) <= target_chars * 1.3:
        yield text
        return

    # Try section-based chunking
    sections = re.split(r'\n(?=##?\s)', text)
    if len(sections) > 1:
        current = ""
        for section in sections:
            if len(current) + len(section) > target_chars and current:
                yield current.strip()
                current = section
            else:
                current += section
        if current.strip():
            yield current.strip()
        return

    # Fallback: paragraph-based chunking
    paragraphs = text.split("\n\n")
    current = ""
    for para in paragraphs:
        if len(current) + len(para) > target_chars and current:
            yield current.strip()
            current = para
        else:
            if current:
                current += "\n\n"
            current += para
    if current.strip():
        yield current.strip()


def chunk_code(text: str, target_chars: int = CHUNK_TARGET_CHARS) -> Iterator[str]:
    """Split code into chunks at function/class boundaries when possible."""
    if len(text) <= target_chars * 1.3:
        yield text
        return

    # Try splitting at top-level def/class
    blocks = re.split(r'\n(?=(?:def |class |async def ))', text)
    current = ""
    for block in blocks:
        if len(current) + len(block) > target_chars and current:
            yield current.strip()
            current = block
        else:
            current += block
    if current.strip():
        yield current.strip()


def chunk_log(text: str, target_chars: int = CHUNK_TARGET_CHARS) -> Iterator[str]:
    """Split log data by lines, grouping into target-sized chunks."""
    lines = text.strip().split("\n")
    current = ""
    for line in lines:
        if len(current) + len(line) > target_chars and current:
            yield current.strip()
            current = line
        else:
            if current:
                current += "\n"
            current += line
    if current.strip():
        yield current.strip()


def extract_frontmatter(text: str) -> tuple[dict, str]:
    """Extract YAML frontmatter and body from a markdown file.

    Returns (frontmatter_dict, body_text).
    """
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text

    # Simple key: value parsing (no pyyaml dependency)
    fm = {}
    for line in parts[1].strip().split("\n"):
        line = line.strip()
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip().strip("'\"")
            # Parse lists: [a, b, c]
            if val.startswith("[") and val.endswith("]"):
                val = [v.strip().strip("'\"") for v in val[1:-1].split(",")]
            fm[key] = val

    return fm, parts[2]


def estimate_tokens(text: str) -> int:
    """Rough token count estimate (~4 chars per token)."""
    return len(text) // CHARS_PER_TOKEN


def read_document(path: Path) -> str:
    """Read a document, extracting text from PDFs if needed.

    For PDFs, requires pymupdf (fitz). Falls back to raw text.
    """
    if path.suffix.lower() == ".pdf":
        try:
            import fitz  # pymupdf
            doc = fitz.open(path)
            pages = [page.get_text() for page in doc]
            doc.close()
            return "\n\n".join(pages)
        except ImportError:
            raise ImportError(
                "PDF support requires pymupdf: pip install pymupdf"
            )
    return path.read_text()


def safe_filename(name: str) -> str:
    """Convert a string to a safe filename: lowercase, hyphens, no special chars."""
    name = name.lower().strip()
    name = re.sub(r'[^a-z0-9\s-]', '', name)
    name = re.sub(r'\s+', '-', name)
    return name[:64]
