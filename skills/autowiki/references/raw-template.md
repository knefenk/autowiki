# autowiki  -  Raw Source Template

Every raw source file saved to `raw/` must follow this format.

## Frontmatter

```yaml
---
source_url: <original URL or file path>
ingested: YYYY-MM-DD
sha256: <hex digest of stripped body>
type: article | paper | code | log | data
repo: <optional, source repository name>
---
<raw content>
```

## sha256 computation

```python
import hashlib
body = "<the raw content>"
sha = hashlib.sha256(body.strip().encode()).hexdigest()
```

**Strip whitespace before hashing.** The file format inserts a newline between
`---` and the body. Stripping normalizes this so drift detection works correctly.

## When drift-checking

```python
parts = content.split("---", 2)
body = parts[2].strip()
current = hashlib.sha256(body.encode()).hexdigest()
# Compare current against stored sha256 in frontmatter
```

## File naming

- `raw/articles/`  -  markdown docs, web articles: `descriptive-slug.md`
- `raw/papers/`  -  PDFs, arxiv papers: `paper-title-slug.md`
- `raw/code/`  -  source code: `<repo-name>/<file-path>.md`
- `raw/logs/`  -  logs, CSVs, JSON data: `system-name-log-type.md`
