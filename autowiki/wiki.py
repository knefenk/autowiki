"""Wiki initialization and structure management."""

import os
import hashlib
from pathlib import Path
from typing import Optional

DEFAULT_WIKI_PATH = "~/wiki"

WIKI_DIRS = [
    "raw/articles", "raw/papers", "raw/code", "raw/logs", "raw/assets",
    "entities", "concepts", "comparisons", "claims", "queries",
]


def get_wiki_path(path: Optional[str] = None) -> Path:
    """Resolve wiki path from env var, argument, or default."""
    if path:
        return Path(path).expanduser().resolve()
    env = os.environ.get("WIKI_PATH", "")
    if env:
        return Path(env).expanduser().resolve()
    return Path(DEFAULT_WIKI_PATH).expanduser().resolve()


def init_wiki(path: Optional[str] = None, domain: str = "General") -> Path:
    """Create a new wiki directory structure with SCHEMA, index, and log."""
    wiki = get_wiki_path(path)
    wiki.mkdir(parents=True, exist_ok=True)

    for d in WIKI_DIRS:
        (wiki / d).mkdir(parents=True, exist_ok=True)

    # SCHEMA.md
    schema = f"""---
title: Wiki Schema
created: {_today()}
updated: {_today()}
type: meta
tags: [meta]
---

# Wiki Schema

## Domain
{domain}

## Conventions
- File names: lowercase, hyphens, no spaces
- Every wiki page starts with YAML frontmatter
- Use `[[wikilinks]]` to link between pages (minimum 2 outbound links per page)
- Every new page must be added to `index.md`
- Every action must be appended to `log.md`

## Frontmatter
```yaml
---
title: Page Title
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: entity | concept | comparison | claim | query
tags: [from taxonomy]
sources: [raw/path/to/source.md]
confidence: high | medium | low
contested: false
contradictions: []
---
```

## Page Thresholds
- Create a page when an entity/concept appears in 2+ sources OR is central to one source
- Split a page when it exceeds ~200 lines
- Archive when content is fully superseded
"""
    (wiki / "SCHEMA.md").write_text(schema)

    # index.md
    index = f"""# Wiki Index

> Content catalog. Every wiki page listed under its type with a one-line summary.
> Read this first to find relevant pages for any query.
> Last updated: {_today()} | Total pages: 0

## Entities

## Concepts

## Comparisons

## Claims

## Queries
"""
    (wiki / "index.md").write_text(index)

    # log.md
    log = f"""# Wiki Log

> Chronological record of all wiki actions. Append-only.
> Format: `## [YYYY-MM-DD] action | subject`

## [{_today()}] create | Wiki initialized
- Domain: {domain}
- Structure created with SCHEMA.md, index.md, log.md
"""
    (wiki / "log.md").write_text(log)

    # _navigate.md — agent orientation (inspired by agent-kernel's AGENTS.md pattern)
    from ._navigate import CONTENT as NAVIGATE_CONTENT
    (wiki / "_navigate.md").write_text(NAVIGATE_CONTENT)

    return wiki


def save_raw_source(wiki: Path, content: str, *, source_url: str,
                    doc_type: str, subdir: str = "articles",
                    filename: Optional[str] = None) -> Path:
    """Save a raw source file with frontmatter and sha256 tracking.

    Args:
        wiki: Wiki root path
        content: Raw document content
        source_url: Original URL or file path
        doc_type: One of article, paper, code, log, data
        subdir: Subdirectory under raw/ (articles, papers, code, logs)
        filename: Optional filename; auto-generated if omitted

    Returns:
        Path to the saved raw file
    """
    dest = wiki / "raw" / subdir
    dest.mkdir(parents=True, exist_ok=True)

    if filename is None:
        import re
        slug = re.sub(r'[^a-z0-9]+', '-', source_url.lower().rsplit("/", 1)[-1])
        filename = f"{slug}.md"

    body = content.strip()
    sha = hashlib.sha256(body.encode()).hexdigest()

    raw = f"""---
source_url: {source_url}
ingested: {_today()}
sha256: {sha}
type: {doc_type}
---
{body}
"""
    out = dest / filename
    out.write_text(raw)
    return out


def compute_sha256(content: str) -> str:
    """Compute sha256 of content with whitespace normalization.

    Strips leading/trailing whitespace to match the file format
    where a newline is inserted between YAML closer and body text.
    """
    return hashlib.sha256(content.strip().encode()).hexdigest()


def read_raw_body(filepath: Path) -> tuple[str, str]:
    """Read a raw source file, return (body, stored_sha256).

    Splits on frontmatter delimiters, strips body whitespace.
    """
    content = filepath.read_text()
    if not content.startswith("---"):
        return content, ""
    parts = content.split("---", 2)
    if len(parts) < 3:
        return content, ""
    import re
    sha_match = re.search(r'sha256:\s*(\S+)', parts[1])
    stored = sha_match.group(1) if sha_match else ""
    body = parts[2].strip()
    return body, stored


def check_drift(filepath: Path) -> bool:
    """Check if a raw source file has drifted from its stored sha256.

    Returns True if drifted (hash mismatch), False if clean.
    """
    body, stored = read_raw_body(filepath)
    if not stored:
        return False
    current = hashlib.sha256(body.encode()).hexdigest()
    return stored != current


def _today() -> str:
    from datetime import date
    return date.today().isoformat()
