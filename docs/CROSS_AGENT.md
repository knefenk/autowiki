# Cross-Agent Interface Design

How multiple AI agents read from and write to the same autowiki knowledge base
without corrupting each other's work. Based on patterns from ENPIRE (git fleet),
Hermes (delegation + kanban), and the LLM Wiki's append-only conventions.

## Design Goals

1. **Multiple readers, multiple writers.** N agents should be able to ingest
   N documents in parallel.
2. **No silent corruption.** If two agents write conflicting claims, the
   conflict must be detected, not silently won by the last writer.
3. **Knowledge propagates.** When agent A discovers something, agent B should
   be able to learn it without re-reading all of A's raw sources.
4. **Minimal coordination overhead.** Agents should not need to lock the entire
   wiki or wait for each other.

## Approach: Git Branches + Shared Index

The core insight from ENPIRE: coordination flows through git, not through a
central server. Each agent works in its own branch; the shared state is the
git history itself.

```
main (canonical KB)
├── agent-a/ingest-enpire-paper
├── agent-b/ingest-autoresearch-readme
├── agent-c/ingest-logs
└── agent-d/validate-claims
```

### Write Protocol (Agent → KB)

1. **Branch off main.** `git checkout -b agent/<name>/<task>`
2. **Read orientation.** Read SCHEMA.md, index.md, recent log.md entries
3. **Ingest document.** Full EN→PI→R→E loop on the branch
4. **Pre-merge validation.** Run `autowiki lint` on the branch. Must pass.
5. **Propose merge.** Push branch, open PR (or signal human for review)
6. **Merge to main.** After review (or auto-merge if low-risk), merge to main
7. **Rebuild index.** `autowiki index --write` on main after merge

### Read Protocol (KB → Agent)

1. **Read index.md.** Get the full catalog of pages.
2. **Search for topics.** `autowiki search "<query>"`
3. **Read specific pages.** `read_file` on relevant markdown files.
4. **Check confidence.** Filter by confidence level. Treat `low` as uncertain.
5. **Check recency.** Check `updated` dates. Prefer recent pages.

### Conflict Detection

Conflicts happen when two agents write about the same entity/concept with
incompatible claims. Detection strategy:

1. **Pre-merge lint.** `autowiki lint` on the branch checks for broken links
   and internal consistency.
2. **Merge-time diff.** When merging to main, the git diff shows which pages
   were created or modified by each agent.
3. **Post-merge reconciliation.** If two branches both modified
   `entities/enpire-framework.md`, the merge will produce a conflict that
   a third agent (or human) resolves.
4. **Claim-level conflict detection.** `autowiki validate` checks for
   contradictions between claims in the merged wiki.

### Shared State: Ingest Queue (`ingest-queue.json`)

To prevent two agents from ingesting the same document:

```json
{
  "queue": [
    {"url": "https://arxiv.org/abs/...", "status": "pending", "agent": null},
    {"url": "https://arxiv.org/abs/...", "status": "claimed", "agent": "agent-a"},
    {"url": "file:///data/logs/production.jsonl", "status": "done", "agent": "agent-b"}
  ],
  "last_updated": "2026-06-21T15:30:00Z"
}
```

Agents atomically claim items (check status == "pending" before claiming).
This is the same pattern as Hermes kanban's task claiming.

### Knowledge Propagation (Cross-Agent Learning)

When agent A ingests a document and discovers something agent B should know:

1. **Index is the propagation channel.** When agent A updates index.md with
   new pages, agent B reads index.md on its next orientation and discovers them.
2. **Wikilinks are the navigation.** When agent B reads a page that links to
   `[[new-concept]]`, agent B can follow the link.
3. **Log is the changelog.** `log.md` records every ingest. Agent B can scan
   recent log entries to see what changed.
4. **Confidence signals attention.** Pages with `contested: true` or
   `confidence: low` are flagged for all agents, not just the original author.

### Comparison to Reference Systems

| | ENPIRE Fleet | Hermes Kanban | AutoWiki Multi-Agent |
|---|---|---|---|
| Coordination | Git worktrees | SQLite board + dispatcher | Git branches + ingest queue |
| Conflict resolution | Git merge (manual or automatic) | Task claim (atomic) | Git merge + lint validation |
| Knowledge sharing | Leaderboard + recipe adoption | Task comments + links | Index + wikilinks + log |
| Isolation | Per-station worktree | Per-worker env vars | Per-agent git branch |
| Durability | Worktrees persist | SQLite persists | Git history persists |

## Implementation Roadmap

### Phase 1: Single-Agent (current)
- One agent, one wiki, sequential ingestion
- `autowiki` Python package + Hermes skill

### Phase 2: Queue-Based Multi-Agent
- `ingest-queue.json` for task claiming
- Atomic claim-and-branch workflow
- Pre-merge `autowiki lint` gate

### Phase 3: Autonomous Fleet
- Cron-scheduled agents pick from queue
- Auto-merge for low-risk changes (new pages, no contradictions)
- Human-in-the-loop for conflicted merges
- Notifications via Hermes gateway on contradictions

### Phase 4: Knowledge Graph API
- `kb-index.json` alongside `index.md` for structured programmatic access
- MCP server exposing `query_kb`, `add_claim`, `validate_kb` tools
- Any MCP-compatible agent can consume the KB
