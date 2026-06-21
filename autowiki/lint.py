"""Lint and health-check the wiki."""

from pathlib import Path
from .validate import ValidationReport, validate_wiki


def lint(wiki_path: Path, verbose: bool = False) -> str:
    """Run a full lint pass and return a human-readable report.

    Args:
        wiki_path: Path to wiki root
        verbose: Include suggested actions for each issue

    Returns:
        Formatted lint report string
    """
    wiki = Path(wiki_path).expanduser().resolve()
    report = validate_wiki(wiki)

    lines = []
    lines.append("=" * 60)
    lines.append(f"AUTOWIKI LINT  -  {wiki}")
    lines.append(f"Total pages: {report.total_pages}")
    lines.append("=" * 60)

    # Group by severity
    issues = []

    if report.broken_links:
        issues.append(("BROKEN LINKS", "SEVERE", report.broken_links,
                       [f"  {p} -> [[{l}]] (page doesn't exist)" for p, l in report.broken_links],
                       "Fix or remove broken wikilinks. They break navigation."))

    if report.drifted_sources:
        issues.append(("SOURCE DRIFT", "SEVERE", report.drifted_sources,
                       [f"  {s}" for s in report.drifted_sources],
                       "Raw source files modified since ingest. Verify changes are intentional."))

    if report.missing_frontmatter:
        issues.append(("MISSING FRONTMATTER", "SEVERE", report.missing_frontmatter,
                       [f"  {p}" for p in report.missing_frontmatter],
                       "Add YAML frontmatter (title, created, updated, type, tags, sources)."))

    if report.contested_pages:
        issues.append(("CONTESTED PAGES", "HIGH", report.contested_pages,
                       [f"  {p}" for p in report.contested_pages],
                       "Pages with flagged contradictions. Human review required."))

    if report.orphans:
        issues.append(("ORPHAN PAGES", "MEDIUM", report.orphans,
                       [f"  {p}" for p in report.orphans],
                       "Pages with no inbound wikilinks. Add links from related pages."))

    if report.underlinked:
        issues.append(("UNDERLINKED PAGES", "MEDIUM", report.underlinked,
                       [f"  {p} ({n} wikilinks, need >=2)" for p, n in report.underlinked],
                       "Add wikilinks to connect these pages to the knowledge graph."))

    if report.low_confidence_pages:
        issues.append(("LOW CONFIDENCE", "LOW", report.low_confidence_pages,
                       [f"  {p}" for p in report.low_confidence_pages],
                       "Pages with low confidence. Seek corroboration or mark for review."))

    if report.oversized_pages:
        issues.append(("OVERSIZED PAGES", "LOW", report.oversized_pages,
                       [f"  {p}" for p in report.oversized_pages],
                       "Pages over 200 lines. Consider splitting into sub-topics."))

    if report.stale_pages:
        issues.append(("STALE PAGES", "LOW", report.stale_pages,
                       [f"  {p}" for p in report.stale_pages],
                       "Pages not updated in 90+ days. Review or archive."))

    if report.pages_without_source:
        issues.append(("MISSING SOURCE", "INFO", report.pages_without_source,
                       [f"  {p}" for p in report.pages_without_source],
                       "Pages without source attribution. Add sources to frontmatter."))

    if not issues:
        lines.append("\n  All checks passed. Wiki is healthy.")
        return "\n".join(lines)

    for name, severity, items, formatted, fix_hint in issues:
        lines.append(f"\n--- {name} ({severity})  -  {len(items)} found ---")
        for f in formatted:
            lines.append(f)
        if verbose:
            lines.append(f"  Fix: {fix_hint}")

    lines.append(f"\n{'=' * 60}")
    total = sum(len(items) for _, _, items, _, _ in issues)
    lines.append(f"SUMMARY: {total} issues across {len(issues)} categories")
    lines.append(f"  SEVERE: {sum(1 for _, s, _, _, _ in issues if s == 'SEVERE')}")
    lines.append(f"  HIGH: {sum(1 for _, s, _, _, _ in issues if s == 'HIGH')}")
    lines.append(f"  MEDIUM: {sum(1 for _, s, _, _, _ in issues if s == 'MEDIUM')}")
    lines.append(f"  LOW: {sum(1 for _, s, _, _, _ in issues if s == 'LOW')}")
    lines.append(f"  INFO: {sum(1 for _, s, _, _, _ in issues if s == 'INFO')}")

    return "\n".join(lines)
