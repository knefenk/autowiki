"""Query the knowledge base."""

import re
from pathlib import Path
from typing import Optional


def search(wiki_path: Path, query: str, *,
           types: Optional[list[str]] = None,
           tags: Optional[list[str]] = None,
           limit: int = 10) -> list[dict]:
    """Search the wiki for pages matching a query.

    Searches page titles, content, and frontmatter tags.

    Args:
        wiki_path: Wiki root
        query: Search terms
        types: Filter by page type (entity, concept, comparison, claim, query)
        tags: Filter by tags
        limit: Max results

    Returns:
        List of {slug, title, type, path, snippet}
    """
    wiki = Path(wiki_path).expanduser().resolve()
    results = []
    query_lower = query.lower()
    query_terms = query_lower.split()

    for section in ("entities", "concepts", "comparisons", "claims", "queries"):
        section_dir = wiki / section
        if not section_dir.exists():
            continue

        # Filter by type if specified
        if types and section not in types:
            continue

        for md_file in section_dir.glob("*.md"):
            content = md_file.read_text()

            # Tag filter
            if tags:
                fm = _parse_frontmatter(content)
                page_tags = fm.get("tags", [])
                if isinstance(page_tags, str):
                    page_tags = [page_tags]
                if not any(t in page_tags for t in tags):
                    continue

            # Score: title match > content match
            score = 0
            title = ""
            for line in content.split("\n"):
                if line.startswith("# ") and not title:
                    title = line[2:].strip()
                    break

            if not title:
                title = md_file.stem.replace("-", " ").title()

            title_lower = title.lower()
            content_lower = content.lower()

            # Title match (weighted higher)
            for term in query_terms:
                if term in title_lower:
                    score += 3
            if query_lower in title_lower:
                score += 5

            # Content match
            for term in query_terms:
                score += content_lower.count(term)

            if score > 0:
                # Extract snippet
                snippet = _extract_snippet(content_lower, query_terms)

                results.append({
                    "slug": md_file.stem,
                    "title": title,
                    "type": section,
                    "path": str(md_file.relative_to(wiki)),
                    "score": score,
                    "snippet": snippet,
                })

    # Sort by score descending, limit
    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:limit]


def get_page(wiki_path: Path, slug: str) -> Optional[dict]:
    """Get a wiki page by slug.

    Returns {slug, title, type, path, content, frontmatter} or None.
    """
    wiki = Path(wiki_path).expanduser().resolve()

    for section in ("entities", "concepts", "comparisons", "claims", "queries"):
        page = wiki / section / f"{slug}.md"
        if page.exists():
            content = page.read_text()
            fm, body = _parse_frontmatter_full(content)

            title = ""
            for line in body.split("\n"):
                if line.startswith("# "):
                    title = line[2:].strip()
                    break

            return {
                "slug": slug,
                "title": title or fm.get("title", slug),
                "type": section,
                "path": str(page.relative_to(wiki)),
                "content": content,
                "frontmatter": fm,
            }

    return None


def list_pages(wiki_path: Path, section: Optional[str] = None) -> list[dict]:
    """List all wiki pages, optionally filtered by section.

    Returns list of {slug, title, type, path}.
    """
    wiki = Path(wiki_path).expanduser().resolve()
    results = []

    sections = [section] if section else ["entities", "concepts", "comparisons", "claims", "queries"]

    for sec in sections:
        section_dir = wiki / sec
        if not section_dir.exists():
            continue
        for md_file in sorted(section_dir.glob("*.md")):
            fm, _ = _parse_frontmatter_full(md_file.read_text())
            title = fm.get("title", md_file.stem.replace("-", " ").title())
            results.append({
                "slug": md_file.stem,
                "title": title,
                "type": sec,
                "path": str(md_file.relative_to(wiki)),
            })

    return results


def _parse_frontmatter(content: str) -> dict:
    """Parse YAML frontmatter into dict."""
    if not content.startswith("---"):
        return {}
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}
    fm = {}
    for line in parts[1].strip().split("\n"):
        line = line.strip()
        if ":" in line:
            key, _, val = line.partition(":")
            fm[key.strip()] = val.strip().strip("'\"")
    return fm


def _parse_frontmatter_full(content: str) -> tuple[dict, str]:
    """Parse frontmatter and return (dict, body)."""
    if not content.startswith("---"):
        return {}, content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content
    return _parse_frontmatter(content), parts[2]


def _extract_snippet(content_lower: str, terms: list[str], context: int = 40) -> str:
    """Extract a relevant snippet around the first matching term."""
    for term in terms:
        idx = content_lower.find(term)
        if idx >= 0:
            start = max(0, idx - context)
            end = min(len(content_lower), idx + len(term) + context)
            snippet = content_lower[start:end].strip()
            if start > 0:
                snippet = "..." + snippet
            if end < len(content_lower):
                snippet = snippet + "..."
            return snippet[:200]
    return ""
