# Installing AutoWiki for OpenCode

## Installation

Add autowiki to the `plugin` array in your `opencode.json`:

```json
{
  "plugin": ["autowiki@git+https://github.com/knefenk/autowiki.git"]
}
```

Restart OpenCode. Verify by asking: "what skills do you have for knowledge bases?"

## Usage

```
use skill tool to load autowiki
ingest this PDF into my wiki at ~/wiki
```

## Updating

```json
{
  "plugin": ["autowiki@git+https://github.com/knefenk/autowiki.git#v0.1.0"]
}
```
