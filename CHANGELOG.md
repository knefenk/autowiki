# Changelog

## 0.1.0 (2026-06-21)

Initial release.

### Core
- EN→PI→R→E ingestion pipeline: chunk documents, extract understanding,
  validate claims, index knowledge
- Support for markdown, PDFs, code files, CSV/TSV, JSON, and log data (JSONL)
- Context-window-efficient chunking: ~3K tokens per chunk, never loads full KB

### Validation
- Source fidelity check: claims verified against raw source text
- Internal consistency check: contradiction detection with `contested` flagging
- Confidence scoring (high/medium/low) on every claim
- Sha256-tracked raw sources with drift detection

### CLI
- `autowiki init`  -  initialize a new wiki
- `autowiki lint`  -  health-check with severity-grouped reporting
- `autowiki search`  -  full-text search with type and tag filters
- `autowiki show`  -  display a wiki page
- `autowiki list`  -  list pages by section
- `autowiki index`  -  rebuild index.md from pages
- `autowiki validate`  -  check raw source drift

### Hermes Skill
- `skills/autowiki/SKILL.md`  -  Agent Skills-compatible skill (165 lines)
- References: raw template, page template, validation example (worked case)

### Documentation
- Cross-agent interface design (git-branch-based multi-agent protocol)
- Trending skills ecosystem survey
- Obsidian vault compatibility
