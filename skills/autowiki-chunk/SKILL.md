---
name: autowiki-chunk
description: "Use when splitting a document into processable chunks. Trigger: 'chunk this file', 'split document for ingestion', 'what chunking strategy for this file'."
version: 0.1.0
author: knefenk
license: MIT
metadata:
  hermes:
    tags: [wiki, chunking, documents]
    category: research
    related_skills: [autowiki-ingest]
---

# AutoWiki Chunk

Split a document into chunks the agent can process without context overflow.
Pick strategy by file type, then read one chunk at a time.

## Strategy selection

| Extension | Strategy | How to split |
|---|---|---|
| `.md`, `.txt` | `prose` | Split at `##` or `#` headers. Fallback: paragraph boundaries (double newline). Target 1K-3K tokens per chunk. |
| `.log`, `.jsonl` | `log` | Three sections: **head** (first 50 lines for format), **middle** (100 lines from center for patterns), **tail** (last 100 lines for recency). |
| `.csv`, `.tsv` | `data` | **Schema** (header row) + **sample** (20 evenly-spaced rows). |
| `.py`, `.js`, `.go` | `code` | Split at `def `, `class `, `async def `. Keep imports and file-level config with first chunk. |

## Prose chunking

Read the file. Find section headers (`## Title` or `# Title`). Split so each
chunk is 1K-3K tokens. If no headers, split at paragraph boundaries (blank
lines). Avoid splitting mid-paragraph.

To read a specific chunk without loading the full file:
```
read_file <file> offset=<N> limit=<M>
```

Skip boilerplate: license headers, table of contents, navigation blocks.

## Log chunking

Read first 50 lines for format identification (head). Sample 100 lines from
the middle third of the file (patterns). Read last 100 lines (recent events).
Skip the rest.

For JSONL: the head section surfaces the schema. Middle sections find error
signatures and outliers. Tail shows most recent events.

## Data chunking

Read the header row for schema. Sample 20 rows evenly distributed through
the file. `step = max(1, total_rows // 20)`. Skip the rest.

Schema + 20 rows is ~500 tokens. Full 10K-row CSV is ~100K tokens. Same
extraction quality for structural understanding.

## Code chunking

Split at top-level function and class boundaries. `import` statements,
file-level constants, and docstrings stay with the first chunk.

Implementation-only functions (getters, I/O helpers) that contain no
novel logic or concepts can be summarized in one line rather than
processed in full. Focus extraction on: novel algorithms, data structures,
configuration that defines system behavior.

## Never

- Load the full file into context — use `offset` and `limit`
- Process the same chunk twice without changing strategy
- Count implementation-only code blocks as "stale" — they're expected
