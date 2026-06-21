---
name: autowiki-init
description: "Use when creating a new autowiki knowledge base. Trigger: 'start a wiki', 'init wiki', 'create knowledge base', 'set up autowiki'."
version: 0.1.0
author: knefenk
license: MIT
metadata:
  hermes:
    tags: [wiki, knowledge-base, init]
    category: research
---

# AutoWiki Init

Create a new knowledge base directory. One-time setup.

## Steps

1. Ask where: `$WIKI` (default `~/wiki`). Ask for domain description.
2. Create directories:

```bash
WIKI="${WIKI_PATH:-$HOME/wiki}"
mkdir -p "$WIKI"/{raw/{articles,papers,code,logs,assets},entities,concepts,comparisons,claims,queries}
```

3. Write `$WIKI/SCHEMA.md` with frontmatter, domain, conventions, tag taxonomy.
   See `references/schema-template.md` for format.

4. Write `$WIKI/index.md` with empty sections (Entities, Concepts, Comparisons, Claims, Queries).

5. Write `$WIKI/log.md` with creation entry.

6. Write `$WIKI/_navigate.md` — agent orientation file. See `references/navigate-template.md`.

7. Report: path + domain + ready for first ingest.

## Verification

```bash
ls "$WIKI"/{SCHEMA.md,index.md,log.md,_navigate.md,entities,concepts,claims,raw}
```
