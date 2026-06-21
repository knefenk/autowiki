# autowiki — micro skill (~600 tokens)

Load this when the full skill is too heavy. Stripped to bare workflow.

## When to use

Document ingestion into a validated knowledge base. For long batch runs
(5+ documents), also set up the watchdog.

## State file

Maintain `$WIKI/state.json`:

```json
{"current_doc": "raw/articles/foo.md", "chunk": 3, "total_chunks": 8,
 "extracted": ["entity-x"], "pages_touched": ["entity-x"],
 "stale_count": 0, "last_seen": 1719000000}
```

Commands:
```bash
python3 scripts/autowiki.py state --init <doc> --total <N> --path $WIKI
python3 scripts/autowiki.py state --set-chunk 3 --add-extracted "entity-x" --path $WIKI
python3 scripts/autowiki.py stale --path $WIKI       # call when chunk yields nothing
python3 scripts/autowiki.py watchdog --path $WIKI     # check if run is alive/stuck
```

## Two-pass loop per chunk

### Pass A: Extract (no KB pages in context)

Context budget: ~1.5K tokens

1. Read ONE chunk (target 1K tokens)
2. Extract: entities, concepts, claims, relationships
3. Write to `$WIKI/.tmp/extracted.json` (append)
4. If chunk yields ZERO extractable items: run `python3 scripts/autowiki.py stale --path $WIKI`
   - stale=1: retry with same chunk size
   - stale=2-3: halve the chunk size and retry
   - stale=4+: skip document, flag for human
5. Update state: `--set-chunk <next>` or `--add-extracted "<name>"`

### Pass B: Integrate (one KB page at a time)

Context budget: ~1.5K tokens per page

1. Read `$WIKI/.tmp/extracted.json`
2. Read `$WIKI/index.md` (scan, don't load fully)
3. For EACH item:
   a. Search: `search_files "<name>" path=$WIKI file_glob="*.md" output_mode="files_only"`
   b. Match exists: read it, update it, write back
   c. No match: create new page (see `references/page-template.md`)
4. Track touched pages in `$WIKI/.tmp/touched.json`

### Validation pass (per chunk)

Context budget: ~1K tokens

1. For each claim: re-read raw source section, compare numbers/qualifiers, assign confidence
2. Search for contradictions in existing claims/

### Independent audit pass (after all chunks)

Run this AFTER the main loop completes. It re-checks claims the main loop might
have gotten wrong. Maker/checker split.

1. Pick 3 claims at random from `$WIKI/.tmp/extracted.json`
2. For each: read the raw source section independently, compare
3. If audit disagrees with original confidence: mark `contested: true`
4. Run `python3 scripts/autowiki.py validate --path $WIKI`

### After all chunks

1. `python3 scripts/autowiki.py index --path $WIKI --write`
2. Append to `$WIKI/log.md`
3. `python3 scripts/autowiki.py validate --path $WIKI`
4. Clean up `$WIKI/.tmp/`
5. Report: pages created/updated, validation flags, audit findings

## Watchdog (for long batch runs)

If processing 5+ documents overnight, run this in a separate session:

```bash
# Check every hour
python3 scripts/autowiki.py watchdog --path $WIKI
```

The watchdog only checks liveness and stuck state. It never reads task data
or modifies pages. Three outcomes:
- `alive: false` → restart from last checkpoint
- `stuck: true, action: nudge` → inject alternative chunking strategy
- `stuck: true, action: flag` → alert human, skip current document

## Chunking

`python3 scripts/autowiki.py chunk --target 4000 <file>`
Target 1K tokens per chunk. Skip boilerplate.

## Never

- Load more than one KB page into context at once
- Load the full index.md — scan filenames from search_files output
- Auto-resolve contradictions — flag for review
- Modify raw/ files
- Let the watchdog read task data — it only checks state.json
