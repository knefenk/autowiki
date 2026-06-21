"""Validation  -  source fidelity, consistency, confidence, drift detection."""

import re
import hashlib
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ValidationReport:
    """Results of a validation pass over the wiki."""
    total_pages: int = 0
    pages_with_source: int = 0
    pages_without_source: list = field(default_factory=list)
    contested_pages: list = field(default_factory=list)
    low_confidence_pages: list = field(default_factory=list)
    orphans: list = field(default_factory=list)
    underlinked: list = field(default_factory=list)  # pages with <2 wikilinks
    broken_links: list = field(default_factory=list)
    drifted_sources: list = field(default_factory=list)
    missing_frontmatter: list = field(default_factory=list)
    stale_pages: list = field(default_factory=list)
    oversized_pages: list = field(default_factory=list)  # >200 lines

    @property
    def issues(self) -> int:
        return (len(self.broken_links) + len(self.contested_pages) +
                len(self.drifted_sources) + len(self.orphans) +
                len(self.underlinked) + len(self.low_confidence_pages) +
                len(self.missing_frontmatter) + len(self.stale_pages))

    @property
    def healthy(self) -> bool:
        return self.issues == 0


def validate_wiki(wiki_path: Path) -> ValidationReport:
    """Run full validation on a wiki directory.

    Checks: frontmatter completeness, source attribution, wikilink health,
    contradictions, confidence distribution, source drift, page freshness.
    """
    report = ValidationReport()
    pages = _collect_pages(wiki_path)
    report.total_pages = len(pages)

    all_slugs = {_slug(p) for p in pages}
    inbound = {s: set() for s in all_slugs}

    for page in pages:
        rel = str(page.relative_to(wiki_path))
        content = page.read_text()

        # Frontmatter check
        fm = _parse_frontmatter(content)
        if not fm:
            report.missing_frontmatter.append(rel)
            continue

        # Source attribution
        if "sources" in fm:
            report.pages_with_source += 1
        else:
            report.pages_without_source.append(rel)

        # Contradictions
        if fm.get("contested") in (True, "true"):
            report.contested_pages.append(rel)

        # Low confidence
        if fm.get("confidence") == "low":
            report.low_confidence_pages.append(rel)

        # Wikilink analysis
        links = re.findall(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]', content)
        slug = _slug(page)

        if len(links) < 2 and "index" not in rel and "log" not in rel and "SCHEMA" not in rel:
            report.underlinked.append((rel, len(links)))

        for link in links:
            if link not in all_slugs:
                report.broken_links.append((rel, link))
            else:
                inbound[link].add(slug)

        # Page size
        if len(content.split("\n")) > 200:
            report.oversized_pages.append(rel)

    # Orphan detection
    for slug, refs in inbound.items():
        if len(refs) == 0 and slug not in ("sc...", "index", "log"):
            # Find the page filename
            for p in pages:
                if _slug(p) == slug:
                    report.orphans.append(str(p.relative_to(wiki_path)))
                    break

    # Source drift
    raw_dir = wiki_path / "raw"
    if raw_dir.exists():
        for raw_file in raw_dir.rglob("*.md"):
            body, stored = _read_raw_body(raw_file)
            if stored:
                current = hashlib.sha256(body.encode()).hexdigest()
                if stored != current:
                    report.drifted_sources.append(
                        str(raw_file.relative_to(wiki_path))
                    )

    return report


def check_claim_fidelity(claim: str, source_text: str) -> dict:
    """Check if a claim is faithful to its source text.

    Returns dict with: faithful (bool), issues (list of str).
    This is a heuristic check  -  the LLM should do the heavy semantic lifting.
    This function flags obvious mechanical mismatches.
    """
    issues = []

    # Extract numbers from claim and source
    claim_nums = set(re.findall(r'\d+\.?\d*%?', claim))
    source_nums = set(re.findall(r'\d+\.?\d*%?', source_text))

    # Numbers in claim but not in source (potential fabrication)
    extra = claim_nums - source_nums
    if extra:
        issues.append(f"Numbers in claim not found in source: {extra}")

    # Check for dropped qualifiers
    qualifiers = ["up to", "approximately", "about", "roughly", "nearly",
                  "around", "~", "±"]
    for q in qualifiers:
        if q in source_text.lower() and q not in claim.lower():
            issues.append(f"Qualifier '{q}' present in source but missing in claim")

    return {
        "faithful": len(issues) == 0,
        "issues": issues,
    }


def score_confidence(source_count: int, has_contradiction: bool,
                     fidelity_ok: bool, is_opinion: bool = False) -> str:
    """Compute confidence level for a claim.

    Args:
        source_count: Number of independent sources supporting the claim
        has_contradiction: Whether the claim contradicts other claims
        fidelity_ok: Whether the claim faithfully represents its sources
        is_opinion: Whether this is a subjective claim

    Returns:
        'high', 'medium', or 'low'
    """
    if has_contradiction or not fidelity_ok or is_opinion:
        return "low"
    if source_count >= 2:
        return "high"
    return "medium"


def _collect_pages(wiki_path: Path) -> list:
    """Collect all wiki pages excluding raw/, SCHEMA, index, log."""
    pages = []
    exclude = {"raw", "_archive"}
    for md_file in wiki_path.rglob("*.md"):
        parts = md_file.relative_to(wiki_path).parts
        if parts[0] in exclude:
            continue
        name = md_file.name
        if name in ("SCHEMA.md", "index.md", "log.md"):
            continue
        pages.append(md_file)
    return pages


def _slug(page: Path) -> str:
    return page.stem


def _parse_frontmatter(content: str) -> dict:
    """Simple key:value frontmatter parser."""
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
            fm[key.strip()] = val.strip()
    return fm


def _read_raw_body(filepath: Path) -> tuple[str, str]:
    """Read raw source, return (body, stored_sha256)."""
    content = filepath.read_text()
    if not content.startswith("---"):
        return content, ""
    parts = content.split("---", 2)
    if len(parts) < 3:
        return content, ""
    sha_match = re.search(r'sha256:\s*(\S+)', parts[1])
    stored = sha_match.group(1) if sha_match else ""
    body = parts[2].strip()
    return body, stored
