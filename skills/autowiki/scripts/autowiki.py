#!/usr/bin/env python3
"""autowiki — mechanical operations for the knowledge base.

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

NAVIGATE_CONTENT="""# Agent Navigation

You are an AI agent. This directory is an autowiki knowledge base.
Read this once to understand how to find and use information here.

## Quick start

1. Read `index.md` - catalog of every page, one line each, grouped by type.
2. Read `SCHEMA.md` if this is your first time - domain, conventions, tag list.
3. `read_file log.md` (last 30 lines) for recent activity.

## Finding things

**By topic:**
```
search_files "<term>" path=. file_glob="*.md" output_mode="files_only"
```

**Structured search:**
```
python3 scripts/autowiki.py search "<query>" --path . --limit 5
```

**By tag or confidence:**
```
search_files "tags:.*framework" path=. file_glob="*.md"
search_files "confidence: low" path=. file_glob="*.md"
```

**Pages linking to X:**
```
search_files "\\\\[\\\\[page-slug\\\\]\\\\]" path=. file_glob="*.md" output_mode="files_only"
```

**List all pages by type:**
```
python3 scripts/autowiki.py list --path . --section entities
python3 scripts/autowiki.py list --path . --section concepts
python3 scripts/autowiki.py list --path . --section claims
```

## Reading a page

Read with `read_file`. The top of each file has YAML frontmatter with:

- `type` - entity | concept | claim | comparison | query
- `confidence` - high | medium | low (low = don't trust without checking source)
- `contested: true` - this page conflicts with another; read both before concluding
- `contradictions: [slug]` - which page it contradicts
- `sources: [raw/...]` - where the information came from
- `tags: [...]` - topics

Follow `[[wikilinks]]` to explore connections. The graph IS the KB.

## Understanding the structure

```
wiki/
├── _navigate.md    <- you are here
├── SCHEMA.md       <- domain, rules, tag taxonomy
├── index.md        <- full catalog (read this first)
├── log.md          <- chronological activity record
├── raw/            <- immutable source documents (never modify)
│   ├── articles/   <- markdown, web pages
│   ├── papers/     <- PDFs, arxiv
│   ├── code/       <- source code snapshots
│   └── logs/       <- log files, CSV, JSON data
├── entities/       <- named things: people, orgs, systems, tools
├── concepts/       <- ideas, techniques, patterns, findings
├── claims/         <- specific assertions with confidence scores
├── comparisons/    <- side-by-side analyses
└── queries/        <- saved answers worth keeping
```

## Verifying the KB

```
python3 scripts/autowiki.py lint --path .
python3 scripts/autowiki.py validate --path .
```

## Rules

- Never load the full KB into context. Search, then read specific pages.
- Never modify files in `raw/` - they're immutable.
- `confidence: low` claims need source verification before being relied on.
- `contested: true` pages have unresolved contradictions - flag for human review.
- Prefer updating an existing page over creating a new one.
- Every new page must be added to `index.md`.
- Every action must be appended to `log.md`.
"""


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
    (wiki / "_navigate.md").write_text(NAVIGATE_CONTENT)
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
    target = args.target or CHUNK_TARGET_CHARS
    for i, chunk in enumerate(chunk_text(text, target)):
        print(f"=== CHUNK {i} ({len(chunk)} chars, ~{len(chunk)//CHARS_PER_TOKEN} tokens) ===")
        if args.dry_run:
            print(f"  First 100 chars: {chunk[:100]}...")
        else:
            print(chunk)
        print()


def cmd_state(args):
    """Read or write progress state for multi-chunk ingestion."""
    wiki = Path(args.path).expanduser().resolve()
    wiki.mkdir(parents=True, exist_ok=True)
    state_file = wiki / "state.json"
    if args.init:
        state = {"current_doc": args.init, "chunk": 0, "total_chunks": args.total or 1,
                 "extracted": [], "pages_touched": []}
        state_file.write_text(json.dumps(state, indent=2))
        print(f"State initialized: {args.init} (0/{state['total_chunks']})")
    elif state_file.exists():
        state = json.loads(state_file.read_text())
        if args.set_chunk is not None:
            state["chunk"] = args.set_chunk
        if args.add_extracted:
            state["extracted"].append(args.add_extracted)
        if args.add_touched:
            if args.add_touched not in state["pages_touched"]:
                state["pages_touched"].append(args.add_touched)
        state_file.write_text(json.dumps(state, indent=2))
        print(json.dumps(state))
    else:
        print(json.dumps({"error": "no state file. use --init to create"}))


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
            s_text = f" — {summary}" if summary else ""
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
        print(f"\n{i+1}. [[{slug}]] ({section}) — score: {score}")
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
    s_chunk.add_argument("--target", type=int, help="Target chars per chunk (default 12K)")
    s_chunk.add_argument("--dry-run", action="store_true")

    s_state = sub.add_parser("state")
    s_state.add_argument("--path", default="~/wiki")
    s_state.add_argument("--init")
    s_state.add_argument("--set-chunk", type=int)
    s_state.add_argument("--total", type=int)
    s_state.add_argument("--add-extracted")
    s_state.add_argument("--add-touched")

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
     "chunk": cmd_chunk, "state": cmd_state, "lint": cmd_lint, "index": cmd_index,
     "search": cmd_search, "show": cmd_show, "list": cmd_list}[args.cmd](args)


if __name__ == "__main__":
    main()
