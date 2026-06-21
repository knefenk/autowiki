# autowiki — user scenario

A walkthrough of what a fresh user experiences, from zero to a working
knowledge base. No jargon, just what happens.

---

## Scene 1: you have documents piling up

You're researching the semiconductor market. You've collected:
- A PDF of TSMC's latest earnings report
- A CSV of SOX index historical data
- Some markdown notes from a conference call
- Server logs from your monitor script

They're in different folders, different formats. You want to extract
what matters and be able to search it later.

## Scene 2: you install autowiki

```
pip install autowiki
```

Or if you use an AI agent:

```
npx skills add https://github.com/knefenk/autowiki
```

## Scene 3: you start a wiki

```
autowiki init --path ~/research-kb --domain "semiconductor market"
```

This creates a directory at `~/research-kb/` with everything set up:
- `_navigate.md` — instructions for AI agents that will read this KB
- `SCHEMA.md` — the rules and tag system
- `index.md` — will become the catalog of everything you know
- Empty folders for entities, concepts, claims, comparisons

## Scene 4: you ingest the first document

You open your AI agent and say:

> "ingest ~/Downloads/tsmc-q1-2026-earnings.pdf into ~/research-kb"

The agent loads the autowiki skill and starts working:

1. It reads the PDF, saves a copy to `raw/papers/`
2. It splits the document into small chunks (about 1K tokens each)
3. For each chunk, it extracts things like:
   - TSMC (entity)
   - Revenue NT$1.13T, +35% YoY (claim)
   - Q1 2026 earnings (concept)
4. For each finding, it checks if a page already exists. If not, creates one
5. It links pages together with `[[wikilinks]]`
6. Claims get a confidence score — if the PDF says it clearly, `high`.
   If it's an estimate or unclear, `medium` or `low`

If a chunk produces nothing useful, the agent notices. After two empty
chunks, it tries a different approach (smaller chunks, re-read the section).
After four, it flags the document for you to look at manually.

## Scene 5: you check the KB

```
autowiki search "TSMC revenue" --path ~/research-kb
```

You get back:

```
1. [[tsmc]] (entities) — score: 12
   TSMC
   "Taiwan Semiconductor Manufacturing Company. Q1 2026 revenue
   NT$1.13T, YoY +35.1%..."

2. [[tsmc-q1-2026-revenue]] (claims) — score: 8
   TSMC Q1 2026 revenue NT$1.13T
   confidence: high, sources: raw/papers/tsmc-earnings-q1-2026.md
```

## Scene 6: you ingest more documents

You add the CSV, conference notes, and server logs. Each time, the agent:
- Finds existing pages and updates them (TSMC already has a page)
- Creates new pages for new entities and concepts
- Cross-references: the SOX data page links to TSMC, ASML, and the
  semiconductor crash framework concept
- Flags contradictions: if the CSV says SOX was at 14,000 but your notes
  say 14,500, both get marked `contested: true` with a note

## Scene 7: you lint the KB

```
autowiki lint --path ~/research-kb
```

```
BROKEN LINKS: 0
CONTESTED PAGES: 1
  claims/sox-index-value.md — contradicts claims/sox-conference-note.md
LOW CONFIDENCE: 2
  claims/asml-bookings-estimate.md — based on single source
  claims/intel-turnaround-timeline.md — opinion, not data
```

You now know exactly what needs attention. No surprises buried in documents.

## Scene 8: you run overnight batch ingest

You have 20 more PDFs. It's late. You run:

```
autowiki ingest --path ~/research-kb --batch ~/Downloads/papers/
```

The agent processes them while you sleep. A watchdog checks every hour:
- Is the run still alive? Check `state.json`'s `last_seen` timestamp.
- Is it stuck? Check the `stale_count`. If it hit the same empty chunk
  3 times, the watchdog nudges it with a different strategy.
- Is it dead? If no heartbeat for 2+ hours, the watchdog restarts from
  the last checkpoint.

In the morning, you run `autowiki lint` and see what was added overnight.
The agent already flagged 3 claims for your review and marked 2 contradictions.

## Scene 9: an AI agent reads the KB

A different agent, weeks later, lands in your KB. It doesn't know anything
about semiconductors. It reads `_navigate.md`:

> "You are an AI agent. This directory is an autowiki knowledge base.
> Read index.md first, then search for what you need."

In under 1K tokens, the agent knows:
- How to search the KB
- What the frontmatter fields mean
- Which directories hold what
- How to follow wikilinks to explore connections
- Never to trust `confidence: low` without checking the source

It finds the TSMC revenue claim, follows the wikilink to the semiconductor
crash framework, sees the contested SOX value, and tells you: "based on
your KB, there's an unresolved discrepancy in SOX index data from Q1."

---

## What the user never sees

- Documents processed in chunks so the agent never runs out of context
- Claims checked against raw sources before being accepted
- Stale counter incrementing silently when chunks yield nothing
- Watchdog polling `state.json` while they sleep
- The independent audit pass double-checking random claims after ingestion
- Sha256 hashes verifying that raw sources haven't been modified
