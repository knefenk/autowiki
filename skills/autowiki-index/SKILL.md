---
name: autowiki-index
description: "Use when updating the knowledge base index and log after ingestion. Trigger: 'rebuild index', 'update wiki index', 'regenerate index', 'update log'."
version: 0.1.0
author: knefenk
license: MIT
metadata:
  hermes:
    tags: [wiki, index, maintenance]
    category: research
    related_skills: [autowiki-ingest, autowiki-validate]
---

# AutoWiki Index

Rebuild `index.md` and update `log.md` after ingestion or changes.

## Rebuild index.md

1. Scan each section directory for `.md` files:
   ```
   search_files "*.md" target=files path=$WIKI/entities
   search_files "*.md" target=files path=$WIKI/concepts
   search_files "*.md" target=files path=$WIKI/claims
   search_files "*.md" target=files path=$WIKI/comparisons
   search_files "*.md" target=files path=$WIKI/queries
   ```

2. For each file, extract title and summary:
   - Read the file
   - Title: from frontmatter `title:` field or first `# ` heading
   - Summary: first non-empty line after title (max 120 chars)

3. Write `$WIKI/index.md`:
   ```markdown
   # Wiki Index

   > Last updated: YYYY-MM-DD | Total pages: N

   ## Entities
   - [[slug]] — summary

   ## Concepts
   - [[slug]] — summary

   ## Claims
   - [[slug]] — summary (confidence: high|medium|low)

   ## Comparisons
   - [[slug]] — summary

   ## Queries
   - [[slug]] — summary
   ```

   Alphabetical within each section. Update total page count.

## Update log.md

Append entry to `$WIKI/log.md`:

```markdown
## [YYYY-MM-DD] <action> | <subject>
- Created: <list of new files>
- Updated: <list of modified files>
- Flags: <contradictions, low confidence, drift>
```

If log.md exceeds 500 entries, rotate: rename to `log-YYYY.md`, start fresh.

## Verification

- Every page in filesystem appears in `index.md`
- No `index.md` entries point to deleted files
- Total count matches filesystem
- Log entry appended

## Never

- Delete index entries — mark as `[MISSING]` instead
- Skip log entries — the log is the audit trail
