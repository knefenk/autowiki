---
name: autowiki
description: "Use when ingesting text-based documents (PDFs, code, CSVs, logs, markdown) into a validated, cross-referenced knowledge base. Triggers: 'add to wiki', 'ingest document', 'compile knowledge', 'validate claims', 'what does my wiki know about X', 'lint the wiki'."
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [wiki, knowledge-compiler, validation, multi-agent, document-processing]
    category: research
    related_skills: [llm-wiki]
---

# AutoWiki — Self-Validating Knowledge Compiler

Ingest documents → extract understanding → validate claims → build a reusable KB.

Built on the LLM Wiki pattern (Karpathy) and the EN→PI→R→E loop (ENPIRE/NVIDIA).
Works as an Obsidian vault out of the box — open `~/wiki` in Obsidian for
graph view, wikilinks, and Dataview queries on frontmatter.

See `references/ecosystem-survey.md` for the competitive landscape (kepano/obsidian-skills,
ARIS, karpathy-llm-wiki) and where autowiki fits.

**What makes this different:** claims are checked against their sources
(did we hallucinate?) and against each other (do claims contradict?).
Every claim gets a confidence score. Raw sources are sha256-tracked for
drift detection.

## Wiki Location

Default: `~/wiki`. Override with `WIKI_PATH` env var.

## Architecture: The EN→PI→R→E Loop

```
EN (Ingestion)  → PI (Understanding) → R (Validation) → E (Index)
```

### EN — Ingestion

1. **Save raw source.** Determine type → save to `raw/<subdir>/` with frontmatter
   (source_url, ingested, sha256 of stripped body, type). See `references/raw-template.md`.

2. **Chunk and extract.** Process one chunk at a time (~3K tokens). Extract entities,
   concepts, claims, relationships. Note provenance (line numbers in source).

3. **Cross-chunk dedup.** Merge duplicates, flag internal contradictions.

### PI — Understanding

1. Search existing KB (`search_files` + `index.md`) for related pages.
2. Create or update pages. Follow `references/page-template.md` for format.
3. Every page: frontmatter with type + tags + sources + confidence, min 2 wikilinks.
4. Tags only from SCHEMA.md taxonomy.

### R — Validation (novel — not in other wiki skills)

**R1 — Source fidelity:** For each claim, re-check against raw source.
Flag: invented numbers, dropped qualifiers, shifted context.

**R2 — Internal consistency:** Search KB for contradicting claims.
If found: mark `contested: true` on both pages, set `confidence: low`,
add contradiction section. Do NOT auto-resolve.

**R3 — Confidence scoring:**
- `high`: 2+ independent sources, no contradictions, fidelity verified
- `medium`: single source, no contradictions, fidelity verified (default)
- `low`: contradiction exists, fidelity concern, or single-source opinion

See `references/validation-example.md` for a worked case (ENPIRE "99% success").

### E — Indexing

1. Add new pages to `index.md` (alphabetical, by type).
2. Append to `log.md`: action, subject, created/updated pages, validation flags.
3. Report: pages created/updated, contradictions, review items.

## Document Type Handling

- **Markdown/text:** Read directly, chunk at section boundaries.
- **PDF:** Use `web_extract` or `pymupdf`. Save to `raw/papers/`.
- **Code (.py, .js, .go, ...):** Save to `raw/code/<repo>/`. Extract module purpose,
  public API, design patterns. File-level granularity.
- **CSV/tabular:** Read header + first 50 rows. Extract schema, value ranges, relationships.
- **Logs (JSONL, .log):** Read tail 200 + middle sample + head 50. Extract format,
  error patterns, timing. Detect crash signatures (near-zero eval time).
- **JSON:** Parse structure, identify schema and relationships.

## Context Window Strategy

The KB IS the context management strategy. Never load all documents.

1. Load ONE chunk (~3K tokens).
2. Search KB for relevant pages (results only, ~1K tokens).
3. Read only pages being edited (~2K tokens).
4. File findings, move to next chunk.

Context at any point: ~6K tokens. Cumulative KB: unlimited.

## Querying

1. Read `index.md` → identify relevant pages.
2. `search_files` for key terms.
3. Read top 3-5 pages, synthesize answer.
4. Cite pages: "Based on [[page-a]] and [[page-b]]..."
5. If answer is substantial synthesis, optionally file to `queries/`.

## Lint

Mechanical checks (auto-fix): broken wikilinks, index completeness, frontmatter
validation, tag taxonomy.

Heuristic checks (report only): contradictions (`contested: true`),
low-confidence pages, orphans, stale content, oversized pages, source drift
(recompute sha256 vs stored).

Report grouped by severity: broken links > contradictions > orphans > low confidence > stale > style.

## Agent Navigation

Every wiki includes `_navigate.md` at its root — a short file any agent can
read to learn how to find and use information in the KB. No skill needed.

```
read_file $WIKI/_navigate.md
```

For ingestion with small context windows (<8K tokens), use the two-pass
approach in `references/micro-skill.md`.

## Cross-Agent Design

- Markdown-native: any agent with file read/search can query
- Git-versioned: contributions via branch + merge (ENPIRE fleet pattern)
- Frontmatter queryable: search by type, tags, confidence, date
- Provenance complete: every claim traces to raw source

See `docs/CROSS_AGENT.md` for the full multi-agent protocol.

## Initialization

```bash
WIKI="${WIKI_PATH:-$HOME/wiki}"
mkdir -p "$WIKI"/{raw/{articles,papers,code,logs,assets},entities,concepts,comparisons,claims,queries}
```

Write SCHEMA.md (ask user for domain), index.md (empty sections), log.md (creation entry).

## Pitfalls

- Never modify raw/ files — sources are immutable
- Never load entire KB into context — search, then read
- Never auto-resolve contradictions — flag for human review
- Always orient first: read SCHEMA + index + recent log
- Claims MUST have wikilinks — link to entity and concept pages
- Claims about metrics need qualification scrutiny (pass@8 vs pass@1)
- Sha256 must be computed on `.strip()`'d body — file format inserts newline between `---` and body. Drift check must also strip before hashing, otherwise every file shows false-positive drift.
- No em dashes in committed files. Use plain hyphens or commas. Check with `grep -r '—' *.md *.py` before committing.
- Squash to single clean commit before first push. No history of fixes, README edits, or style corrections in the initial commit.
- README tone: fact-based, humble, mention inspirations, invite PRs
- GitHub push: prefer SSH (`git@github.com:user/repo.git`). Fine-grained tokens don't work for git HTTPS push. Classic tokens need `repo` + `workflow` scopes. If token auth fails with "Password authentication is not supported", use SSH or generate a new key with `ssh-keygen -t ed25519` and add to github.com/settings/keys.

## Documentation Style

When writing READMEs, project docs, or wiki pages for this user:

- **Fact-based, no jargon.** State what the thing does, not how great it is.
  No marketing words: \"powerful\", \"comprehensive\", \"seamless\", \"advanced\".
- **Mention inspirations directly.** \"Built from X, Y, and Z\" with links.
  The user wants the lineage visible.
- **Simple and direct.** Short sentences. No \"heterogeneous document ingestion
  pipeline\" when \"reads PDFs, code, CSVs, logs\" says the same thing.
- **Show, don't sell.** Include example output, concrete what-it-catches lists,
  real commands — not value propositions.

The README rewrite in the initial autowiki session is the reference example:
went from \"Self-validating knowledge compiler — ingest heterogeneous documents\"
to \"Turn documents into a searchable, cross-referenced knowledge base.\"

## Obsidian Compatibility

The wiki IS an Obsidian vault:
- `[[wikilinks]]` render as clickable links
- Graph View visualizes the knowledge network
- YAML frontmatter powers Dataview queries (`TABLE tags FROM "entities" WHERE contains(tags, "framework")`)
- `raw/assets/` holds images referenced via `![[image.png]]`

## Installation

```bash
# Agent Skills (Claude Code, Codex, Cursor, Hermes)
npx skills add https://github.com/knefenk/autowiki

# Python package
pip install autowiki

# Hermes-only (no pip — uses scripts/autowiki.py)
cp -r skills/autowiki ~/.hermes/skills/research/autowiki
```

The Hermes-only path uses `scripts/autowiki.py` (self-contained, 280 lines)
for mechanical operations (chunking, sha256, lint, index rebuild). The LLM
handles semantic work. No pip, no external deps — just Python 3.10+.

For mechanical ops, call: `python3 scripts/autowiki.py <command> --path ~/wiki`
where commands are: init, save-raw, validate, chunk, lint, index, search, show, list.

See `references/ecosystem-survey.md` for the Agent Skills landscape
surveyed during development (kepano/obsidian-skills, ARIS, karpathy-llm-wiki).
