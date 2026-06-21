# Contributing to autowiki

## What to contribute

- **Bug reports.** If the ingestion pipeline produces wrong claims, if
  validation misses contradictions, if drift detection misfires  -  open an issue.
- **New document type support.** The pipeline handles markdown, code, CSV,
  logs, JSON, and PDFs. If you need another format, PRs welcome.
- **Validation improvements.** The source fidelity and consistency checks
  are heuristics  -  better ones are always welcome.
- **Cross-agent integrations.** If you want autowiki to work with Claude Code,
  Codex, Cursor, or another agent framework, add a skills mirror.

## Development

```bash
git clone https://github.com/knefenk/autowiki
cd autowiki
pip install -e ".[dev]"
python -m pytest tests/ -v
```

## Code style

- Lean. No unnecessary abstractions.
- Every module has a clear single responsibility.
- Functions over classes where possible.
- Type hints on public APIs.

## Skill contributions

The SKILL.md at `skills/autowiki/SKILL.md` follows the Agent Skills spec.
References and templates live in `skills/autowiki/references/`.

Skill standards:
- SKILL.md under 200 lines
- description field ≤ 60 chars with concrete triggers
- author field credits humans first

## Commit conventions

```
type: subject

Optional body.
```

Types: `fix:`, `feat:`, `refactor:`, `docs:`, `chore:`
