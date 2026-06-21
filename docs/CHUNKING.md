# Chunking strategy for token-efficient ingestion

How autowiki splits documents for LLM consumption. Different strategies
for different data types, optimized for extraction quality per token.

## The problem

Naive chunking wastes tokens on:
- Repetitive log lines (same pattern, different timestamps)
- Tabular data (1000 rows where 10 samples + schema would suffice)
- Boilerplate (license headers, imports, table of contents)
- Already-extracted content (re-reading the same section)

## Strategy per type

### Prose (markdown, articles, papers)
Split at section headers (`##`, `#`). Fall back to paragraph boundaries.
Target: 1K-3K tokens per chunk. This keeps each chunk semantically coherent.

### Logs (JSONL, .log, syslog)
**Don't chunk every line.** Three-part sampling:
1. **Head (50 lines):** identify format, fields, timestamp pattern
2. **Middle (100 lines, sampled):** find patterns, error signatures, anomalies
3. **Tail (100 lines):** most recent events

Extract the *template* of each log pattern, not every instance.
"ERROR: connection timeout to host X" repeated 500 times = one pattern + count.

### CSV / tabular data
1. **Schema first:** read header + 5 rows to understand columns and types
2. **Statistical sample:** 20 rows evenly distributed
3. **Full data only if:** the LLM needs exact values for claim extraction

Schema + 20 rows is ~500 tokens. Full 10K-row CSV is ~100K tokens.
Same extraction quality for most purposes.

### Code (Python, JS, etc.)
1. **Skip imports, license headers, docstrings** (already handled by source preservation)
2. **Chunk at function/class boundaries:** each chunk is one logical unit
3. **Extract API surface:** function signatures, class definitions, key constants
4. **Skip implementation details** unless the LLM needs them for a claim

### JSON / structured data
1. **Extract schema** from keys and types
2. **Sample values** for representative entries
3. **Full object only** if it's small (<500 chars)

## Token budget per document type

| Type | Strategy | Typical tokens per doc |
|---|---|---|
| Article/paper (5K words) | Section chunks, 2-3K each | 3-5K total |
| Log file (10K lines) | Head + middle + tail sampling | 2-3K total |
| CSV (5K rows) | Schema + 20-row sample | 500-1K total |
| Code file (500 lines) | Function-level chunks | 1-2K per file |
| JSON (large object) | Schema + sample values | 500-1K total |

## Implementation

The `scripts/autowiki.py chunk` command now supports `--strategy`:

```bash
# Prose (default): section boundaries
autowiki chunk doc.md --strategy prose

# Log: head+middle+tail sampling
autowiki chunk server.log --strategy log

# Data: schema + sample rows
autowiki chunk data.csv --strategy data

# Code: function boundaries
autowiki chunk module.py --strategy code
```
