"""State tracking for multi-chunk document ingestion.

Tracks progress, detects when chunks yield nothing (stale detection),
and provides liveness checking for long-running batch jobs.
"""

import json
import time
from pathlib import Path
from typing import Optional


def init_state(wiki: Path, doc: str, total_chunks: int) -> dict:
    """Initialize state for a new ingestion run."""
    wiki.mkdir(parents=True, exist_ok=True)
    state = {
        "current_doc": doc, "chunk": 0, "total_chunks": total_chunks,
        "extracted": [], "pages_touched": [],
        "stale_count": 0, "last_seen": None,
    }
    (wiki / "state.json").write_text(json.dumps(state, indent=2))
    return state


def read_state(wiki: Path) -> Optional[dict]:
    """Read current ingestion state. Returns None if no state file."""
    sf = wiki / "state.json"
    if not sf.exists():
        return None
    return json.loads(sf.read_text())


def update_state(wiki: Path, **kwargs) -> dict:
    """Update state fields. Returns new state."""
    state = read_state(wiki) or {}
    if "chunk" in kwargs:
        state["chunk"] = kwargs["chunk"]
    if "add_extracted" in kwargs:
        state.setdefault("extracted", []).append(kwargs["add_extracted"])
    if "add_touched" in kwargs:
        if kwargs["add_touched"] not in state.setdefault("pages_touched", []):
            state["pages_touched"].append(kwargs["add_touched"])
    state["last_seen"] = time.time()
    (wiki / "state.json").write_text(json.dumps(state, indent=2))
    return state


def mark_stale(wiki: Path) -> dict:
    """Increment the stale counter. Returns status dict with suggestion."""
    state = read_state(wiki)
    if not state:
        return {"error": "no state file"}
    state["stale_count"] = state.get("stale_count", 0) + 1
    state["last_seen"] = time.time()
    (wiki / "state.json").write_text(json.dumps(state, indent=2))
    c = state["stale_count"]
    if c < 2:
        return {"stale_count": c, "suggestion": "retry with same approach"}
    elif c < 4:
        return {"stale_count": c, "suggestion": "change chunk size or skip ahead"}
    return {"stale_count": c, "suggestion": "flag this document for human review"}


def check_watchdog(wiki: Path) -> dict:
    """Check if an ingestion run is alive, stuck, or dead. Never reads task data."""
    state = read_state(wiki)
    if not state:
        return {"alive": False, "reason": "no state file"}
    last_seen = state.get("last_seen")
    stale = state.get("stale_count", 0)
    chunk = state.get("chunk", 0)
    total = state.get("total_chunks", 0)
    now = time.time()
    if last_seen and (now - last_seen) > 7200:
        return {"alive": False, "reason": f"last seen {int((now-last_seen)/60)}m ago",
                "action": f"restart from chunk {chunk}"}
    if stale >= 4:
        return {"alive": True, "stuck": True, "stale_count": stale,
                "suggestion": "flag for human review", "action": "flag"}
    if stale >= 2:
        return {"alive": True, "stuck": True, "stale_count": stale,
                "suggestion": "change chunking strategy or skip current document",
                "action": "nudge"}
    return {"alive": True, "stuck": False, "progress": f"{chunk}/{total}",
            "stale_count": stale}
