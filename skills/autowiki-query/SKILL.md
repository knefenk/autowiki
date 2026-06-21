---
name: autowiki-query
description: "Use when searching or exploring a knowledge base. Trigger: 'what does the wiki know about X', 'search the KB', 'find pages about', 'show me claims on', 'browse wiki'."
version: 0.1.0
author: knefenk
license: MIT
metadata:
  hermes:
    tags: [wiki, query, search, explore]
    category: research
    related_skills: [autowiki-index]
---

# AutoWiki Query

Search and exploration patterns for a knowledge base.

## Quick orientation

Read `_navigate.md` for KB structure. Read `index.md` for full catalog.

## Search by topic

```
search_files "<term>" path=$WIKI file_glob="*.md" output_mode="files_only"
```

Refine with more terms. Check both entities/ and concepts/ directories.

## Filtered search

**By type:**
```
search_files "<term>" path=$WIKI/claims file_glob="*.md" output_mode="files_only"
```

**By confidence level:**
```
search_files "confidence: low" path=$WIKI file_glob="*.md"
```

**By tag:**
```
search_files "tags:.*framework" path=$WIKI file_glob="*.md"
```

**Find pages linking to a specific page:**
```
search_files "\[\[page-slug\]\]" path=$WIKI file_glob="*.md" output_mode="files_only"
```

## Read and synthesize

1. Read the top 3-5 matching pages with `read_file`.
2. Note frontmatter: `confidence`, `contested`, `sources`.
3. Follow `[[wikilinks]]` to explore related pages.
4. If `contested: true`, read the linked contradiction page too.
5. Synthesize answer. Cite pages: "Based on [[page-a]] and [[page-b]]..."

## Answer confidence

Your answer's confidence = the lowest confidence among cited pages.
If you cite a `confidence: low` page, qualify your answer accordingly.

## Save valuable answers

If the synthesis is substantial (novel connection, deep comparison),
offer to file it to `queries/` as a new page.

## Quick stats

```bash
echo "Entities: $(ls $WIKI/entities/*.md 2>/dev/null | wc -l)"
echo "Concepts: $(ls $WIKI/concepts/*.md 2>/dev/null | wc -l)"
echo "Claims: $(ls $WIKI/claims/*.md 2>/dev/null | wc -l)"
echo "Low confidence: $(grep -rl 'confidence: low' $WIKI/claims/ 2>/dev/null | wc -l)"
echo "Contested: $(grep -rl 'contested: true' $WIKI/ 2>/dev/null | wc -l)"
```

## Never

- Load the full KB into context — search, then read
- Trust `confidence: low` without checking the source
- Ignore `contested: true` — read both sides
