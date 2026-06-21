# Trending Skills Ecosystem  -  Structure Patterns Learned

Survey of top GitHub repos using the Agent Skills / SKILL.md pattern.
Compiled 2026-06-21 from live repo inspection.

## The Landscape

| Repo | Stars | Approach | Key Pattern |
|---|---|---|---|
| [kepano/obsidian-skills](https://github.com/kepano/obsidian-skills) | 36K | 5 focused skill dirs | Reference impl for Agent Skills spec |
| [wanshuiyin/ARIS](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep) | 12K | 83 skill dirs, multi-model | Skills-as-pipeline, cross-model mirrors |
| [OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files) | 23K | Single-skill, file-based | Crash-proof markdown plans |
| [microsoft/SkillOpt](https://github.com/microsoft/SkillOpt) | 8K | Text-space optimizer | TRAIN skills from trajectories |
| [Astro-Han/karpathy-llm-wiki](https://github.com/Astro-Han/karpathy-llm-wiki) | 1.2K | Single SKILL.md | Direct competitor to autowiki |
| [mohitagw15856/pm-claude-skills](https://github.com/mohitagw15856/pm-claude-skills) | 1K | 174 professional skills | Quantity-over-specialization approach |

## Structural Patterns

### 1. SKILL.md is the contract

Every repo uses a `SKILL.md` file (capitalized) as the skill's entry point.
The frontmatter fields are standardizing:

```yaml
---
name: skill-name           # lowercase-hyphens
description: "..."         # triggers + capability, one sentence
---
```

The `description` field is the discovery mechanism  -  agents match against it
to decide when to activate the skill. It must name concrete triggers.

### 2. Directory layout conventions

**Single-skill repos** (karpathy-llm-wiki, planning-with-files):
```
SKILL.md              # at repo root
references/           # templates, examples
assets/               # images
```

**Multi-skill repos** (ARIS, obsidian-skills):
```
skills/
  <skill-name>/
    SKILL.md
    references/
    templates/
    scripts/
```

### 3. ARIS's 83-skill pipeline model

ARIS doesn't have ONE research skill  -  it has a **pipeline of skills**:
`idea-discovery` → `experiment-plan` → `run-experiment` → `analyze-results` →
`paper-write` → `auto-review-loop`. Each skill is a single stage in the pipeline.

This is the ENPIRE loop expressed as discrete skills:
- EN: `serverless-modal`, `vast-gpu` (environment setup)
- PI: `experiment-plan`, `ablation-planner` (policy improvement)
- R: `run-experiment`, `monitor-experiment`, `analyze-results` (rollout)
- E: `research-wiki`, `wiki-enrich`, `auto-review-loop` (evolution)

### 4. Cross-model mirrors

ARIS maintains separate skill variants for different coding agents:
- `skills-codex/`  -  Codex-optimized
- `skills-codex-claude-review/`  -  Codex skills + Claude review
- `skills-codex-gemini-review/`  -  Codex skills + Gemini review

Pattern: same capability, different agent-specific phrasing. This is a
distribution strategy  -  reach users on any platform.

### 5. References/ and templates/ keep SKILL.md lean

The best SKILL.md files are ~150-200 lines  -  just the workflow and rules.
Detailed templates, examples, and reference docs live in `references/`.
This keeps the skill loadable in one context chunk.

### 6. Lint as first-class operation

karpathy-llm-wiki's lint is the gold standard:
- **Deterministic checks** (auto-fix): index consistency, broken links, raw references
- **Heuristic checks** (report only): contradictions, stale claims, orphans, missing cross-refs

This is exactly the autowiki R (Validation) phase, but expressed as lint categories.
The split between auto-fix and report-only is the right UX: the agent fixes
mechanical issues, flags semantic issues for human review.

## What autowiki can learn

### What we already have that's competitive

- EN→PI→R→E loop with validation layer  -  no other skill has this
- Sha256-tracked raw sources with drift detection  -  unique
- Confidence scoring  -  not in any surveyed skill
- Cross-agent interface design  -  not in any surveyed skill

### What we're missing (from the ecosystem)

1. **description field is underspecified.** Our current description: "Compile documents into a validated, cross-referenced wiki." Should include concrete triggers: "Use when ingesting PDFs, code, CSVs, or log data into a knowledge base; when asked to 'add to wiki', 'compile knowledge', or 'validate claims'."

2. **No references/ directory.** Our SKILL.md is 411 lines  -  too long. Extract templates (raw file format, page format) to `references/`. Target ~200 lines for SKILL.md.

3. **Single SKILL.md vs multi-skill.** Right now autowiki is one monolithic skill. Should we split into `autowiki-ingest`, `autowiki-validate`, `autowiki-lint`? ARIS's pipeline model suggests yes for production, but single-skill is better for v0 discovery.

4. **Cross-model compatibility.** We only target Hermes. ARIS has Codex/Claude/Gemini mirrors. Worth considering  -  a `skills/autowiki-codex/` and `skills/autowiki-claude/` could expand reach significantly.

5. **No "Installation" section.** kepano/karpathy-llm-wiki both have `npx skills add` or `/plugin marketplace add` instructions. We need this for discoverability.

6. **Obsidian integration is table stakes.** kepano/obsidian-skills exists because Obsidian is the dominant personal KB tool. Our wiki SHOULD work as an Obsidian vault  -  we already have markdown + wikilinks + frontmatter. We should document this explicitly.

## Action Items for autowiki

1. **Shorten SKILL.md.** Move templates to `references/`. Target 200 lines.
2. **Improve description.** Add concrete triggers. "Use when..."
3. **Document Obsidian compatibility.** It's already compatible  -  say so.
4. **Add installation instructions.** `npx skills add` + manual clone.
5. **Keep single-skill for v0.** Pipeline split later if needed.
6. **Add cross-model mirrors as stretch.** Codex and Claude versions.
