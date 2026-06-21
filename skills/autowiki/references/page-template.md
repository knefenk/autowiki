# autowiki  -  Wiki Page Template

Every wiki page (entity, concept, claim, comparison, query) must follow this format.

## Frontmatter (required)

```yaml
---
title: Page Title
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: entity | concept | comparison | claim | query
tags: [from SCHEMA.md taxonomy]
sources: [raw/path/to/source.md]
confidence: high | medium | low
contested: false
contradictions: []
---
```

## Body structure

```markdown
# Page Title

Opening paragraph  -  what this is, why it matters.
Provenance marker ^[raw/path/to/source.md] on claims from 3+ sources.

## Section Header

Content with [[wikilinks]] to other pages (minimum 2 per page).

## Another Section

More content.

## Related Pages

- [[related-page-1]]
- [[related-page-2]]
```

## Rules

- **Minimum 2 wikilinks per page.** Isolated pages are invisible.
- **Provenance markers** `^[raw/path/to/source.md]` on claims synthesizing 3+ sources.
- **Tags only from SCHEMA.md taxonomy.** Add new tags to SCHEMA.md first.
- **Scannable in 30 seconds.** Split pages over ~200 lines.
- **Confidence scoring:** high (2+ sources, no contradictions) / medium (single source) / low (contradiction or fidelity issue).

## Page types

- **entity**  -  Named thing: person, org, system, model, repo, tool
- **concept**  -  Idea, technique, architecture, pattern, finding
- **claim**  -  Specific assertion with source trace and confidence
- **comparison**  -  Side-by-side analysis (use tables)
- **query**  -  Filed answer worth keeping
