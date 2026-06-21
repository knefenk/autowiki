CONTENT = """# Agent Navigation

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
search_files "\\[\\[page-slug\\]\\]" path=. file_glob="*.md" output_mode="files_only"
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
