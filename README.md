# autowiki

[![CI](https://github.com/knefenk/autowiki/actions/workflows/ci.yml/badge.svg)](https://github.com/knefenk/autowiki/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Turn documents into a validated, cross-referenced knowledge base. Ingests
markdown, PDFs, code, CSVs, logs. Checks that extracted claims match their
sources and don't contradict each other.

The wiki that doesn't trust itself. Documents go in, claims get checked
against their sources, contradictions get flagged instead of buried.

## Install

```bash
# Agent Skills (Claude Code, Codex, Cursor, Hermes, OpenCode, OpenClaw)
npx skills add https://github.com/knefenk/autowiki

# Hermes
hermes skills tap add knefenk/autowiki

# Python (supplementary)
pip install autowiki
```

## Skills

Five focused skills, each loaded independently. An agent loading only what
it needs uses 0.3K-1.7K tokens instead of one large skill at 2.2K. This
split-skill approach follows the pattern from [Superpowers](https://github.com/obra/superpowers)
(235K stars).

| Skill | Does | Tokens |
|---|---|---|
| `autowiki-init` | Create a wiki directory | ~290 |
| `autowiki-ingest` | EN-PI-R loop: chunk, extract, integrate, validate, stuck detection | ~1.7K |
| `autowiki-validate` | Drift check, contradiction detection, lint | ~826 |
| `autowiki-index` | Rebuild index.md and log.md | ~501 |
| `autowiki-query` | Search and exploration patterns | ~581 |

Each skill tells the agent what to do using its native tools -- no scripts
required. The ingest skill is a loop: "for each chunk: extract, search KB,
update pages, validate, next chunk." If a chunk yields nothing, the agent
tries a different approach instead of digging deeper.

## How it works

```
Document → chunk → extract → validate → cross-reference → write pages
```

1. **Read.** Document is split with a strategy picked by type: section
   boundaries for prose, head+middle+tail for logs, schema+sample for
   CSV, function boundaries for code. Raw source saved with sha256 so
   later changes get flagged.

2. **Extract.** Entities, concepts, and claims pulled from each chunk.
   Source provenance tracked (which file, which section).

3. **Validate.** Claims checked two ways: against the raw source (did we
   get the numbers right?) and against existing wiki pages (does this
   contradict something already known?).

4. **Write.** Pages created in `entities/`, `concepts/`, `claims/` with
   frontmatter, wikilinks, and confidence scores.

The wiki is plain markdown files. Every wiki includes `_navigate.md` at
its root -- a short file any agent can read to learn how to find and use
information in the KB without loading anything else. This pattern comes
from [agent-kernel](https://github.com/benjaminsehl/agent-kernel).

## Platform support

| Platform | Install |
|---|---|
| Claude Code | `/plugin marketplace add knefenk/autowiki` |
| Codex | Plugin marketplace |
| Cursor / Windsurf | `npx skills add https://github.com/knefenk/autowiki` |
| Hermes | `hermes skills tap add knefenk/autowiki` |
| OpenCode | Add to `opencode.json` plugin array |
| OpenClaw | `openclaw.plugin.json` |
| pip | `pip install autowiki` |

## Use

```bash
# Start a wiki
autowiki init --path ~/wiki --domain "semiconductor market research"
```

Then in your agent:
```
# Ingest a document
"ingest this PDF into ~/wiki"

# Ask questions
"what does my wiki know about TSMC Q1 revenue?"
"show me low-confidence claims about ASML bookings"
```

Or with the CLI:
```bash
autowiki search "P/E valuation" --path ~/wiki
autowiki validate --path ~/wiki
autowiki lint --path ~/wiki
```

## What the validation catches

- **Dropped qualifiers.** Source says "up to 95%" -- claim says "95%".
- **Metric gaming.** Abstract says "99% success" -- body reveals it's
  pass@8, not pass@1. Flagged at `confidence: medium`.
- **Contradictions.** Page A says X, page B says Y about the same thing.
  Both marked `contested: true`, not silently resolved.
- **Source drift.** Raw file changed after ingest? Sha256 mismatch flags it.
- **Simulated data.** A log file that looks real but is generated -- flagged
  at `confidence: low`.

## Inspirations

- [Karpathy's LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) -- three-layer architecture, markdown-native, wikilinks
- [ENPIRE](https://research.nvidia.com/labs/gear/enpire/) (NVIDIA, 2026) -- EN-PI-R-E closed loop, git-based coordination
- [autoresearch](https://github.com/karpathy/autoresearch) (Karpathy, 2026) -- agent-driven experiment loop, `program.md` pattern
- [Superpowers](https://github.com/obra/superpowers) (235K stars) -- split-skill structure, pure SKILL.md approach
- [agent-kernel](https://github.com/benjaminsehl/agent-kernel) -- AGENTS.md pattern, state/narrative/raw separation
- [Loop Engineering](https://github.com/cobusgreyling/loop-engineering) -- designing systems that prompt agents, not prompting them directly
- [Deli_AutoResearch](https://victorchen96.github.io/auto_research/framework.html) -- stall detection, heartbeat watchdog, direction diversity

## Contributing

Discussions, issues, and PRs welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT
