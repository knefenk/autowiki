# autowiki

[![CI](https://github.com/knefenk/autowiki/actions/workflows/ci.yml/badge.svg)](https://github.com/knefenk/autowiki/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Turn documents into a searchable, cross-referenced knowledge base. Ingests
markdown, PDFs, code, CSVs, logs, and JSON. Checks that extracted claims
match their sources and don't contradict each other.

Built from three earlier projects: Karpathy's [LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
(structure and conventions), NVIDIA's [ENPIRE](https://research.nvidia.com/labs/gear/enpire/)
(closed-loop agent pattern), and Karpathy's [autoresearch](https://github.com/karpathy/autoresearch)
(agent-driven experimentation). The validation step (checking claims against
sources and flagging contradictions) is the main addition on top of those ideas.
Still early  -  if something's off or could be better, open an issue or PR.

## Install

```bash
# Agent Skills (Claude Code, Codex, Cursor, Hermes)
npx skills add https://github.com/knefenk/autowiki

# Python package
pip install autowiki
```

## How it works

```
Document → chunk → extract → validate → cross-reference → write pages
```

1. **Read.** Document is split into chunks (~3K tokens each). Raw source
   is saved with a sha256 hash so later changes get flagged.

2. **Extract.** Entities, concepts, and claims are pulled from each chunk.
   Source provenance is tracked (which file, which section).

3. **Validate.** Claims are checked two ways: against the raw source (did
   we get the numbers right?) and against existing wiki pages (does this
   contradict something already known?).

4. **Write.** Pages are created in `entities/`, `concepts/`, `claims/`
   with frontmatter, wikilinks, and confidence scores.

The wiki is plain markdown files. Open it in Obsidian, VS Code, or any
editor. No database.

## Use

```bash
# Start a wiki
autowiki init --path ~/wiki --domain "semiconductor market research"

# Run the ingestion (via the skill in your agent)
# "ingest this PDF into my wiki"

# Check KB health
autowiki lint --path ~/wiki

# Search
autowiki search "P/E valuation" --path ~/wiki

# Show a page
autowiki show semi-monitor --path ~/wiki

# Check if raw sources changed since ingest
autowiki validate --path ~/wiki
```

## What the validation catches

- **Dropped qualifiers.** Source says "up to 95%" → claim says "95%".
- **Metric gaming.** Paper abstract says "99% success" → body reveals
  it's pass@8, not pass@1. Flagged at `confidence: medium`.
- **Contradictions.** Page A says X, page B says Y about the same thing.
  Both marked `contested: true`, not silently resolved.
- **Source drift.** Raw file changed after ingest? Sha256 mismatch flags it.
- **Simulated data.** A log file that looks real but is generated → flagged
  at `confidence: low`.

## Inspirations

- [Karpathy's LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)  -  three-layer architecture (raw → wiki → schema), markdown-native, wikilinks, log.md conventions
- [ENPIRE](https://research.nvidia.com/labs/gear/enpire/) (NVIDIA/CMU/Berkeley, 2026)  -  the EN→PI→R→E closed loop, git-based multi-agent coordination, idea tree visualization
- [autoresearch](https://github.com/karpathy/autoresearch) (Karpathy, 2026)  -  agent-driven experiment loop, keep/revert via git, `program.md` as agent instructions
- [Agent Skills spec](https://github.com/kepano/obsidian-skills) (kepano, 36K stars)  -  SKILL.md format, `npx skills add` distribution, references/ conventions

## Requirements

Python 3.10+. pymupdf optional for PDFs.

## Contributing

Discussions, issues, and PRs are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT
