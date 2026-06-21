"""Index and log management for the wiki."""

from pathlib import Path
from datetime import date
from typing import Optional


def rebuild_index(wiki_path: Path) -> str:
    """Rebuild index.md from the current wiki pages.

    Scans entities/, concepts/, comparisons/, claims/, queries/
    and builds a sectioned index with page titles and summaries.
    """
    sections = {
        "entities": [],
        "concepts": [],
        "comparisons": [],
        "claims": [],
        "queries": [],
    }

    for section in sections:
        section_dir = wiki_path / section
        if not section_dir.exists():
            continue
        for md_file in sorted(section_dir.glob("*.md")):
            title, summary = _extract_page_info(md_file)
            slug = md_file.stem
            if title:
                sections[section].append((slug, title, summary))

    today = date.today().isoformat()
    total = sum(len(v) for v in sections.values())

    lines = [
        "# Wiki Index",
        "",
        "> Content catalog. Every wiki page listed under its type with a one-line summary.",
        "> Read this first to find relevant pages for any query.",
        f"> Last updated: {today} | Total pages: {total}",
        "",
    ]

    for section, pages in sections.items():
        lines.append(f"## {section.title()}")
        if pages:
            for slug, title, summary in pages:
                summary_text = f"  -  {summary}" if summary else ""
                lines.append(f"- [[{slug}]]{summary_text}")
        lines.append("")

    return "\n".join(lines)


def append_log(wiki_path: Path, action: str, subject: str,
               details: Optional[list[str]] = None) -> None:
    """Append an entry to log.md.

    Args:
        wiki_path: Wiki root
        action: One of ingest, update, query, lint, create, archive, delete
        subject: What was acted on (e.g., source title)
        details: Optional list of bullet points
    """
    log_path = wiki_path / "log.md"
    today = date.today().isoformat()

    entry = f"\n## [{today}] {action} | {subject}\n"
    if details:
        for d in details:
            entry += f"- {d}\n"

    with open(log_path, "a") as f:
        f.write(entry)


def check_log_rotation(wiki_path: Path, max_entries: int = 500) -> bool:
    """Check if log.md needs rotation (>max_entries).

    Returns True if rotation was performed.
    """
    log_path = wiki_path / "log.md"
    if not log_path.exists():
        return False

    content = log_path.read_text()
    entries = content.count("\n## [")
    if entries <= max_entries:
        return False

    # Rotate: rename to log-YYYY.md, start fresh
    today = date.today().isoformat()
    archive_name = f"log-{today[:4]}.md"
    log_path.rename(wiki_path / archive_name)

    log_path.write_text(f"""# Wiki Log

> Chronological record of all wiki actions. Append-only.
> Previous entries archived to {archive_name}.

## [{today}] rotate | Log rotated ({entries} entries archived to {archive_name})
""")
    return True


def update_page_metadata(wiki_path: Path, slug: str, **kwargs) -> None:
    """Update frontmatter fields on an existing wiki page.

    Args:
        wiki_path: Wiki root
        slug: Page slug (without .md)
        **kwargs: Fields to update (e.g., updated="2026-06-21", confidence="high")
    """
    # Find the page
    for section in ("entities", "concepts", "comparisons", "claims", "queries"):
        page = wiki_path / section / f"{slug}.md"
        if page.exists():
            break
    else:
        raise FileNotFoundError(f"Page not found: {slug}")

    content = page.read_text()
    if not content.startswith("---"):
        return

    parts = content.split("---", 2)
    if len(parts) < 3:
        return

    # Update frontmatter
    fm_lines = parts[1].strip().split("\n")
    updated_lines = []
    updated_keys = set()

    for line in fm_lines:
        stripped = line.strip()
        if ":" in stripped:
            key = stripped.split(":", 1)[0].strip()
            if key in kwargs:
                updated_lines.append(f"{key}: {kwargs[key]}")
                updated_keys.add(key)
                continue
        updated_lines.append(line)

    # Add new keys that weren't in the original frontmatter
    for key, val in kwargs.items():
        if key not in updated_keys:
            updated_lines.append(f"{key}: {val}")

    new_fm = "\n".join(updated_lines)
    new_content = f"---\n{new_fm}\n---{parts[2]}"
    page.write_text(new_content)


def _extract_page_info(md_file: Path) -> tuple[str, str]:
    """Extract title and summary from a wiki page.

    Returns (title, summary). Summary is first non-title, non-empty line.
    """
    content = md_file.read_text()
    lines = content.split("\n")

    title = ""
    summary = ""

    in_frontmatter = False
    for line in lines:
        if line.strip() == "---":
            in_frontmatter = not in_frontmatter
            continue
        if in_frontmatter:
            if line.startswith("title:"):
                title = line.split(":", 1)[1].strip().strip('"')
            continue
        if line.startswith("# ") and not title:
            title = line[2:].strip()
            continue
        if title and line.strip() and not line.startswith("#") and not line.startswith(">"):
            # First substantive line after the title
            summary = line.strip()
            # Clean up wikilinks and markers
            import re
            summary = re.sub(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]', r'\1', summary)
            summary = re.sub(r'\^\[.*?\]', '', summary)
            summary = summary[:120]  # Truncate long summaries
            break

    return title, summary
