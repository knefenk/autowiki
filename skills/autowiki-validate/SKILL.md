---
name: autowiki-validate
description: "Use when checking knowledge base health. Trigger: 'validate the wiki', 'check for contradictions', 'audit claims', 'lint the KB', 'drift check', 'health check'."
version: 0.1.0
author: knefenk
license: MIT
metadata:
  hermes:
    tags: [wiki, validation, audit]
    category: research
    related_skills: [autowiki-ingest]
---

# AutoWiki Validate

Health checks on the knowledge base. Two passes: mechanical (auto-fix)
and semantic (report only).

## Quick orientation

Read `$WIKI/index.md` for page catalog. Read `$WIKI/SCHEMA.md` for rules.

## Mechanical checks (auto-fix where possible)

### Broken wikilinks

For every `[[link]]` in wiki pages:
```
search_files "\[\[.*\]\]" path=$WIKI file_glob="*.md"
```
Check each link target exists. Fix obvious typos. Flag unresolvable ones.

### Orphan pages

Pages with zero inbound wikilinks. Find them:
```
# For each page slug, search how many other pages link to it
search_files "\[\[<slug>\]\]" path=$WIKI file_glob="*.md" output_mode="count"
```
Zero-count pages = orphans. Add cross-references from related pages.

### Index completeness

Compare `index.md` against actual files in entities/, concepts/, claims/, comparisons/, queries/.
Add missing entries. Mark entries pointing to deleted files as `[MISSING]`.

### Frontmatter validation

Every wiki page must have: `title`, `created`, `updated`, `type`, `tags`, `sources`.
Tags must be in `SCHEMA.md` taxonomy. Add missing fields where possible.
Flag unresolvable ones.

### Tag audit

Extract all tags in use:
```
search_files "tags:.*" path=$WIKI file_glob="*.md"
```
Compare against `SCHEMA.md` taxonomy. Flag tags not in taxonomy.

## Semantic checks (report only, never auto-fix)

### Contradictions

Find all pages with `contested: true` or `contradictions:` in frontmatter.
List them for human review. For each pair, note: what conflicts, which sources,
which is newer.

### Low confidence

List all pages with `confidence: low`. For each: why (single source? fidelity issue?
opinion?). Suggest sources that could corroborate.

### Stale content

Pages whose `updated` date is >90 days behind the most recent source that
mentions the same entity. Check by comparing `updated` in frontmatter against
dates in `log.md`.

### Source drift

For each file in `raw/`:
```bash
for f in "$WIKI"/raw/**/*.md; do
  stored=$(grep '^sha256:' "$f" | awk '{print $2}')
  body=$(sed '1,/^---$/d' "$f" | tail -n +2)
  current=$(echo "$body" | python3 -c "import hashlib,sys; print(hashlib.sha256(sys.stdin.read().strip().encode()).hexdigest())")
  [ "$stored" != "$current" ] && echo "DRIFT: $f"
done
```

### Oversized pages

Pages over 200 lines. Suggest splitting.

## Report format

Group by severity:
1. **Severe:** broken links, drift, missing frontmatter
2. **High:** contradictions, contested pages
3. **Medium:** orphans, underlinked, low confidence
4. **Low:** stale content, oversized, tag issues

Output with file paths and suggested actions.

## Post-validation

Append to `$WIKI/log.md`:
```
## [YYYY-MM-DD] lint | N issues found, M auto-fixed
```

Update `index.md` if entries were added or fixed.

## Never

- Auto-resolve contradictions — flag only
- Delete pages — mark as `[MISSING]`, let human decide
- Modify `raw/` files — they're immutable
