---
name: autowiki-ingest
description: "Use when adding documents to a knowledge base. Trigger: 'ingest document', 'add to wiki', 'process PDF', 'compile knowledge', 'ingest this file into my KB'."
version: 0.1.0
author: knefenk
license: MIT
metadata:
  hermes:
    tags: [wiki, ingest, documents]
    category: research
    related_skills: [autowiki-init, autowiki-validate, autowiki-index]
---

# AutoWiki Ingest

The EN→PI→R loop for document ingestion. Process one document at a time.
For batch runs (5+ docs), run a watchdog session in parallel.

## Before you start

- Wiki must exist with `_navigate.md`, `SCHEMA.md`, `index.md`, `log.md`.
- Read `_navigate.md` to understand directory layout and conventions.
- Read `index.md` for existing pages and `log.md` (last 30 lines) for recent activity.

## State tracking

Use `$WIKI/state.json` to survive context resets:

```
{"current_doc": "...", "chunk": 0, "total_chunks": N,
 "extracted": [], "pages_touched": [], "stale_count": 0, "last_seen": <ts>}
```

Read state at session start. Update after each chunk. If state exists,
resume from where it left off.

## Step 1: Capture raw source

**First, check if already ingested.** Compute sha256 of the document
content. Search existing raw/ files for this sha256:

```bash
grep -rl "sha256: <digest>" "$WIKI"/raw/ 2>/dev/null
```

If found and the user didn't explicitly request re-ingestion, skip this
document. Report: "Already ingested as <path>. Skipping."

If no match, proceed:

1. Read the document. Use `read_file` for text/code/logs. For PDFs,
   extract text first: `python3 -c "import fitz; ..."` or paste content.

2. Save to `raw/<subdir>/<descriptive-slug>.md` with frontmatter:

```yaml
---
source_url: <url or file path>
ingested: YYYY-MM-DD
sha256: <hex>
type: article|paper|code|log|data
---
<content>
```

Compute sha256: `python3 -c "import hashlib,sys; print(hashlib.sha256(sys.stdin.read().strip().encode()).hexdigest())" < <file>`

Subdir: PDFs → `papers/`, code → `code/<repo>/`, logs/CSV → `logs/`, rest → `articles/`.

## Step 2: Chunk with strategy

Load `autowiki-chunk` skill for chunking strategy and instructions.
Pick strategy by file extension:

| Extension | Strategy |
|---|---|
| `.md`, `.txt` | `prose` |
| `.log`, `.jsonl` | `log` |
| `.csv`, `.tsv` | `data` |
| `.py`, `.js`, `.go` | `code` |

Load ONE chunk at a time. Process it fully before loading the next.
To read specific lines: `read_file <file> offset=<N> limit=<M>`.

Implementation-only code blocks that yield no extractable concepts are
normal — don't count them as stale. Only increment `stale_count` when a
chunk yields ZERO items.

## Step 3: EN — Extract (per chunk)

From the current chunk, pull out:

- **Entities:** named things (people, orgs, systems, tools, repos)
- **Concepts:** ideas, techniques, patterns, findings
- **Claims:** assertions of fact with numbers or comparisons
- **Relationships:** entity A relates to entity B via concept C

Note the provenance: which file, which section/line numbers.

Write extracted items to `$WIKI/.tmp/extracted.json` (append mode, one JSON object per line).

**If a chunk yields ZERO extractable items:**
- Mark it: increment `stale_count` in `state.json`
- stale=1: retry same chunk, same strategy
- stale=2-3: halve the chunk size and retry. Don't dig deeper.
- stale≥4: flag this document for human review, skip to next doc

**Important:** implementation-only code blocks that yield no extractable
concepts are normal for the `code` strategy. Only increment `stale_count`
when a block yields ZERO items. Processing details without extracting
new knowledge is expected, not a stall.

**If a block references entities from earlier blocks** (e.g., function
using FEATURE_NAMES from imports block), search the current document's
already-extracted items before creating duplicate pages. Two functions
doing the same thing = one concept page. Update the existing page rather
than creating a new one.

**If extraction succeeds:** proceed to PI phase. Don't touch `stale_count`.
Update `state.json`: increment chunk counter, set `last_seen` timestamp.

## Step 4: PI — Understand and integrate

For each extracted item (entity, concept, claim):

1. **Search KB for existing page:**
   ```
   search_files "<name>" path=$WIKI file_glob="*.md" output_mode="files_only"
   ```

2. **If matching page exists:** read it, update with new information,
   add the new source to frontmatter `sources:` list, add cross-references.
   Bump `updated` date. Write back.

3. **If no match:** create new page using the template below.
   File at `entities/<slug>.md` or `concepts/<slug>.md` or `claims/<slug>.md`.

4. **Every page must have YAML frontmatter:**
   ```yaml
   ---
   title: Page Title
   created: YYYY-MM-DD
   updated: YYYY-MM-DD
   type: entity|concept|claim
   tags: [from SCHEMA.md taxonomy]
   sources: [raw/path/to/source.md]
   confidence: high|medium|low
   contested: false
   contradictions: []
   ---
   ```

5. **Minimum 2 `[[wikilinks]]` per page.** Link to related entities, concepts.
   Pages without links are invisible in the knowledge graph.

6. Track touched pages: add slug to `pages_touched` in `state.json`.

## Step 5: R — Validate (per chunk)

Before moving to next chunk:

1. **Source fidelity:** for each claim, re-read the raw source section.
   Compare numbers, qualifiers, context. If claim text doesn't match source,
   set `confidence: low` and add a note.

2. **Internal consistency:** search claims/ for conflicting claims:
   ```
   search_files "<topic>" path=$WIKI/claims file_glob="*.md" output_mode="files_only"
   ```
   If found: mark both `contested: true`, add `contradictions: [other-slug]`,
   set `confidence: low` on the newer claim. Do NOT auto-resolve.

3. **Confidence scoring:**
   - `high`: 2+ independent sources, no contradictions, fidelity verified
   - `medium`: single source, no contradictions (default for new claims)
   - `low`: contradiction exists, fidelity issue, or single-source opinion

## Step 6: After all chunks

1. Load `autowiki-index` skill to rebuild index and log.
2. Run independent audit: pick 3 claims at random. Re-read their raw sources.
   If audit disagrees with original confidence, mark `contested: true`.
3. Run drift check on all raw sources:
   ```bash
   for f in "$WIKI"/raw/**/*.md; do
     stored=$(grep '^sha256:' "$f" | cut -d' ' -f2)
     body=$(sed '1,/^---$/d' "$f" | tail -n +2)
     current=$(echo "$body" | python3 -c "import hashlib,sys; print(hashlib.sha256(sys.stdin.read().strip().encode()).hexdigest())")
     [ "$stored" != "$current" ] && echo "DRIFT: $f"
   done
   ```
4. Clean up `$WIKI/.tmp/` and `$WIKI/state.json`.
5. Report: pages created, updated, contradictions found, drift detected.

## Watchdog (run in parallel for batch jobs)

In a separate session, check every hour:
```bash
state=$(cat "$WIKI/state.json" 2>/dev/null)
```
- No state file → run hasn't started.
- `last_seen` > 2h ago → run is dead. Restart from chunk in state.
- `stale_count` ≥ 2 → run is stuck. Nudge by injecting alternative chunk size.
- `stale_count` ≥ 4 → flag for human.

The watchdog never reads document content or wiki pages. Only `state.json`.

## Never

- Load more than one KB page into context at once.
- Load the full index.md — scan `search_files` output.
- Auto-resolve contradictions.
- Modify `raw/` files.
- Let the watchdog read task data.
