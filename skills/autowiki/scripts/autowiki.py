#!/usr/bin/env python3
"""autowiki  -  mechanical operations for the knowledge base.

This script handles deterministic operations: init, chunking, sha256,
drift detection, linting, index rebuild. The LLM handles semantic work:
extraction, cross-referencing, confidence scoring, page writing.

Run via: python3 scripts/autowiki.py <command> [args]
"""

import argparse
import hashlib
import os
import re
import json
import sys
from datetime import date
from pathlib import Path
from typing import Optional
from collections import defaultdict

CHARS_PER_TOKEN = 4
CHUNK_TARGET_TOKENS = 3000
CHUNK_TARGET_CHARS = CHUNK_TARGET_TOKENS * CHARS_PER_TOKEN
WIKI_DIRS = [
    "raw/articles", "raw/papers", "raw/code", "raw/logs", "raw/assets",
    "entities", "concepts", "comparisons", "claims", "queries",
]


# ── wiki init ──────────────────────────────────────────────

def cmd_init(args):
    wiki = Path(args.path).expanduser().resolve()
    wiki.mkdir(parents=True, exist_ok=True)
    for d in WIKI_DIRS:
        (wiki / d).mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    domain = args.domain or "General"

    (wiki / "SCHEMA.md").write_text(f"""---
title: Wiki Schema
created: {today}
updated: {today}
type: meta
tags: [meta]
---

# Wiki Schema
## Domain
{domain}
## Conventions
- File names: lowercase, hyphens, no spaces
- Every wiki page starts with YAML frontmatter
- Use `[[wikilinks]]` to link between pages (min 2 per page)
- Every new page must be added to index.md
- Every action appended to log.md
""")
    (wiki / "index.md").write_text(f"# Wiki Index\n\n> Last updated: {today} | Total pages: 0\n\n## Entities\n\n## Concepts\n\n## Comparisons\n\n## Claims\n\n## Queries\n")
    (wiki / "log.md").write_text(f"# Wiki Log\n\n## [{today}] create | Wiki initialized\n- Domain: {domain}\n")
    print(f"Wiki initialized at {wiki}")


# ── raw source management ──────────────────────────────────

def compute_sha256(text: str) -> str:
    return hashlib.sha256(text.strip().encode()).hexdigest()


def cmd_save_raw(args):
    """Save a file as a raw source with sha256 frontmatter."""
    wiki = Path(args.path).expanduser().resolve()
    source = Path(args.file).expanduser().resolve()
    content = source.read_text()
    sha = compute_sha256(content)
    subdir = args.type or "articles"
    dest = wiki / "raw" / subdir
    dest.mkdir(parents=True, exist_ok=True)
    name = re.sub(r'[^a-z0-9]+', '-', source.stem.lower())[:60] + ".md"
    raw = f"""---
source_url: file://{source}
ingested: {date.today().isoformat()}
sha256: {sha}
type: {args.type or 'article'}
---
{content.strip()}
"""
    out = dest / name
    out.write_text(raw)
    print(f"Saved: {out.relative_to(wiki)} ({len(content)} chars, sha256:{sha[:12]}...)")


def cmd_validate(args):
    """Check raw sources for drift."""
    wiki = Path(args.path).expanduser().resolve()
    raw_dir = wiki / "raw"
    drifted = []
    for f in raw_dir.rglob("*.md"):
        content = f.read_text()
        if not content.startswith("---"):
            continue
        parts = content.split("---", 2)
        if len(parts) < 3:
            continue
        m = re.search(r'sha256:\s*(\S+)', parts[1])
        if not m:
            continue
        stored = m.group(1)
        current = compute_sha256(parts[2])
        if stored != current:
            drifted.append(str(f.relative_to(wiki)))
    if drifted:
        print(f"DRIFT in {len(drifted)} files:")
        for d in drifted:
            print(f"  {d}")
    else:
        print("All raw sources unchanged.")


# ── chunking ───────────────────────────────────────────────

def chunk_text(text: str, target: int = CHUNK_TARGET_CHARS):
    """Split text at section boundaries, fallback to paragraphs."""
    if len(text) <= target * 1.3:
        yield text; return
    sections = re.split(r'\n(?=##?\s)', text)
    if len(sections) > 1:
        cur = ""
        for s in sections:
            if len(cur) + len(s) > target and cur:
                yield cur.strip(); cur = s
            else:
                cur += s
        if cur.strip(): yield cur.strip()
        return
    paras = text.split("\n\n")
    cur = ""
    for p in paras:
        if len(cur) + len(p) > target and cur:
            yield cur.strip(); cur = p
        else:
            cur += ("\n\n" if cur else "") + p
    if cur.strip(): yield cur.strip()


def cmd_chunk(args):
    """Print chunk boundaries for a file (for the LLM to use)."""
    text = Path(args.file).expanduser().resolve().read_text()
    for i, chunk in enumerate(chunk_text(text)):
        print(f"=== CHUNK {i} ({len(chunk)} chars, ~{len(chunk)//CHARS_PER_TOKEN} tokens) ===")
        if args.dry_run:
            print(f"  First 100 chars: {chunk[:100]}...")
        else:
            print(chunk)
        print()


# ── lint ───────────────────────────────────────────────────

def parse_frontmatter(content: str) -> dict:
    if not content.startswith("---"):
        return {}
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}
    fm = {}
    for line in parts[1].strip().split("\n"):
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip().strip("'\"")
    return fm


def cmd_lint(args):
    """Health-check the wiki."""
    wiki = Path(args.path).expanduser().resolve()
    pages = []
    for d in WIKI_DIRS[5:]:  # entities, concepts, comparisons, claims, queries
        pdir = wiki / d
        if pdir.exists():
            for f in pdir.glob("*.md"):
                pages.append(f)

    report = defaultdict(list)
    all_slugs = {f.stem for f in pages}
    inbound = {s: set() for s in all_slugs}
    broken = []
    underlinked = []
    orphans_candidates = set(all_slugs)
    low_conf = []
    contested = []
    no_source = []

    for page in pages:
        rel = str(page.relative_to(wiki))
        content = page.read_text()
        fm = parse_frontmatter(content)
        slug = page.stem

        if not fm:
            report["missing_frontmatter"].append(rel)
        if "sources" not in fm:
            no_source.append(rel)
        if fm.get("contested") in (True, "true"):
            contested.append(rel)
        if fm.get("confidence") == "low":
            low_conf.append(rel)

        links = re.findall(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]', content)
        if len(links) < 2:
            underlinked.append((rel, len(links)))
        for l in links:
            if l not in all_slugs:
                broken.append((rel, l))
            else:
                inbound[l].add(slug)

    for slug in all_slugs:
        if inbound.get(slug, set()):
            orphans_candidates.discard(slug)

    # Print
    severity = [
        ("BROKEN LINKS", broken, lambda x: f"  {x[0]} -> [[{x[1]}]]"),
        ("MISSING FRONTMATTER", report["missing_frontmatter"], lambda x: f"  {x}"),
        ("CONTESTED", contested, lambda x: f"  {x}"),
        ("UNDERLINKED (<2 links)", underlinked, lambda x: f"  {x[0]} ({x[1]} links)"),
        ("ORPHANS (no inbound)", sorted(orphans_candidates), lambda x: f"  {x}"),
        ("LOW CONFIDENCE", low_conf, lambda x: f"  {x}"),
        ("NO SOURCE", no_source, lambda x: f"  {x}"),
    ]
    total = 0
    for label, items, fmt in severity:
        n = len(items)
        total += n
        if n:
            print(f"\n{label}: {n}")
            for item in items:
                print(fmt(item))
    if total == 0:
        print("All checks passed.")


# ── index rebuild ──────────────────────────────────────────

def cmd_index(args):
    """Rebuild index.md from wiki pages."""
    wiki = Path(args.path).expanduser().resolve()
    sections = defaultdict(list)
    for section in ["entities", "concepts", "comparisons", "claims", "queries"]:
        pdir = wiki / section
        if not pdir.exists():
            continue
        for f in sorted(pdir.glob("*.md")):
            content = f.read_text()
            title = f.stem.replace("-", " ").title()
            summary = ""
            in_fm = False
            for line in content.split("\n"):
                if line.strip() == "---":
                    in_fm = not in_fm; continue
                if in_fm:
                    if line.startswith("title:"):
                        title = line.split(":", 1)[1].strip().strip('"')
                    continue
                if line.startswith("# ") and not summary:
                    continue
                if line.strip() and not line.startswith("#") and not line.startswith(">"):
                    summary = re.sub(r'\[\[.*?\]\]', '', line.strip())[:100]
                    break
            sections[section].append((f.stem, title, summary))

    today = date.today().isoformat()
    total = sum(len(v) for v in sections.values())
    lines = ["# Wiki Index", "", f"> Last updated: {today} | Total pages: {total}", ""]
    for s, pages in sections.items():
        lines.append(f"## {s.title()}")
        for slug, title, summary in pages:
            s_text = f"  -  {summary}" if summary else ""
            lines.append(f"- [[{slug}]]{s_text}")
        lines.append("")

    output = "\n".join(lines)
    if args.write:
        (wiki / "index.md").write_text(output)
        print(f"index.md rebuilt ({total} pages)")
    else:
        print(output)


# ── search ─────────────────────────────────────────────────

def cmd_search(args):
    """Full-text search across wiki pages."""
    wiki = Path(args.path).expanduser().resolve()
    query = args.query.lower()
    terms = query.split()
    results = []

    for section in ["entities", "concepts", "comparisons", "claims", "queries"]:
        pdir = wiki / section
        if not pdir.exists():
            continue
        for f in pdir.glob("*.md"):
            content = f.read_text()
            score = 0
            for t in terms:
                score += content.lower().count(t)
            if query in content.lower():
                score += 5
            if score > 0:
                title = f.stem.replace("-", " ").title()
                for line in content.split("\n"):
                    if line.startswith("# "):
                        title = line[2:].strip(); break
                idx = content.lower().find(terms[0])
                snippet = content[max(0, idx-30):idx+100].strip()
                results.append((score, f.stem, title, section, snippet[:200]))

    results.sort(key=lambda r: r[0], reverse=True)
    for i, (score, slug, title, section, snippet) in enumerate(results[:args.limit or 10]):
        print(f"\n{i+1}. [[{slug}]] ({section})  -  score: {score}")
        print(f"   {title}")
        if snippet:
            print(f"   \"{snippet}\"")


# ── show ───────────────────────────────────────────────────

def cmd_show(args):
    wiki = Path(args.path).expanduser().resolve()
    for section in ["entities", "concepts", "comparisons", "claims", "queries"]:
        p = wiki / section / f"{args.slug}.md"
        if p.exists():
            print(p.read_text())
            return
    print(f"Page not found: {args.slug}")


# ── list ───────────────────────────────────────────────────

def cmd_list(args):
    wiki = Path(args.path).expanduser().resolve()
    for section in (["entities", "concepts", "comparisons", "claims", "queries"]
                    if not args.section else [args.section]):
        pdir = wiki / section
        if pdir.exists():
            for f in sorted(pdir.glob("*.md")):
                print(f"  [{section}] {f.stem}")


# ── main ───────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(prog="autowiki", description="KB mechanical operations")
    sub = p.add_subparsers(dest="cmd")

    s_init = sub.add_parser("init")
    s_init.add_argument("--path", default="~/wiki")
    s_init.add_argument("--domain", default="General")

    s_save = sub.add_parser("save-raw")
    s_save.add_argument("file")
    s_save.add_argument("--path", default="~/wiki")
    s_save.add_argument("--type", default="article")

    s_val = sub.add_parser("validate")
    s_val.add_argument("--path", default="~/wiki")

    s_chunk = sub.add_parser("chunk")
    s_chunk.add_argument("file")
    s_chunk.add_argument("--dry-run", action="store_true")

    s_lint = sub.add_parser("lint")
    s_lint.add_argument("--path", default="~/wiki")

    s_idx = sub.add_parser("index")
    s_idx.add_argument("--path", default="~/wiki")
    s_idx.add_argument("--write", action="store_true")

    s_search = sub.add_parser("search")
    s_search.add_argument("query")
    s_search.add_argument("--path", default="~/wiki")
    s_search.add_argument("--limit", type=int, default=10)

    s_show = sub.add_parser("show")
    s_show.add_argument("slug")
    s_show.add_argument("--path", default="~/wiki")

    s_list = sub.add_parser("list")
    s_list.add_argument("--path", default="~/wiki")
    s_list.add_argument("--section")

    args = p.parse_args()
    if not args.cmd:
        p.print_help(); return

    {"init": cmd_init, "save-raw": cmd_save_raw, "validate": cmd_validate,
     "chunk": cmd_chunk, "lint": cmd_lint, "index": cmd_index,
     "search": cmd_search, "show": cmd_show, "list": cmd_list}[args.cmd](args)


if __name__ == "__main__":
    main()
