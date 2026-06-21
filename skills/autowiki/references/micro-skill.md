# autowiki — micro skill (~500 tokens)

Load this when the full skill is too heavy. Stripped to bare workflow.
All explanation lives in `references/`.

## When to use

Document ingestion into a validated knowledge base.

## State file

Maintain `$WIKI/state.json` to track progress across chunks:

```json
{"current_doc": "raw/articles/foo.md", "chunk": 3, "total_chunks": 8,
 "extracted": ["entity-x", "concept-y"], "pages_touched": ["entity-x"]}
```

Read state at start. Update after each chunk completes.

## Two-pass loop per chunk

### Pass A: Extract (no KB pages in context)

Context budget: ~1.5K tokens (this file + chunk + temp write)

1. Read ONE chunk from the current document (target 1K tokens)
2. Extract: entities, concepts, claims, relationships
3. Write to `$WIKI/.tmp/extracted.json` (append mode)
4. Update state.json: increment chunk counter

### Pass B: Integrate (one KB page at a time)

Context budget: ~1.5K tokens per page (this file + extracted items + one KB page)

1. Read `$WIKI/.tmp/extracted.json`
2. Read `$WIKI/index.md` for page list (scan, don't load fully)
3. For EACH extracted entity/concept/claim:
   a. Search KB: `search_files "<name>" path=$WIKI file_glob="*.md" output_mode="files_only"`
   b. If matching page exists: read it, update it, write back
   c. If no match: create new page using `references/page-template.md`
   d. Update `$WIKI/.tmp/touched.json` to track what was modified
4. After ALL items processed for this chunk: run validation pass

### Validation (separate pass, optional)

Context budget: ~1K tokens

1. For each claim in `$WIKI/.tmp/extracted.json`:
   a. Re-read the raw source section that produced it
   b. Compare claim text vs source text (numbers, qualifiers)
   c. Assign confidence
2. Check for contradictions against existing claims (search_files for "<topic>" in claims/)

### After all chunks

1. Run `python3 scripts/autowiki.py index --path $WIKI --write`
2. Append to `$WIKI/log.md`
3. Run `python3 scripts/autowiki.py validate --path $WIKI`
4. Clean up `$WIKI/.tmp/`
5. Report to user: pages created, updated, validation findings

## Chunking

Use `python3 scripts/autowiki.py chunk <file>` to get chunk boundaries.
Target 1K tokens per chunk. Skip boilerplate (license headers, table of contents).

## Never

- Load more than one KB page into context at once
- Load the full index.md — scan filenames from search_files output
- Auto-resolve contradictions — flag for review
- Modify raw/ files
