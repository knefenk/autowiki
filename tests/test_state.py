"""Tests for stuck detection, watchdog, and state tracking — no subprocess."""

import json, time, tempfile
from pathlib import Path
from autowiki.wiki import init_wiki
from autowiki.state import init_state, read_state, update_state, mark_stale, check_watchdog


def test_stale_counter_increments():
    with tempfile.TemporaryDirectory() as tmp:
        wiki = init_wiki(tmp)
        init_state(wiki, "test-doc", 5)

        r1 = mark_stale(wiki)
        assert r1["stale_count"] == 1
        assert "retry" in r1["suggestion"]

        r2 = mark_stale(wiki)
        assert r2["stale_count"] == 2
        assert "change chunk" in r2["suggestion"]

        mark_stale(wiki)
        r4 = mark_stale(wiki)
        assert r4["stale_count"] == 4
        assert "human" in r4["suggestion"]


def test_watchdog_detects_stuck():
    with tempfile.TemporaryDirectory() as tmp:
        wiki = init_wiki(tmp)
        init_state(wiki, "test", 5)

        r = check_watchdog(wiki)
        assert r["alive"] == True
        assert r["stuck"] == False

        mark_stale(wiki)
        mark_stale(wiki)
        r = check_watchdog(wiki)
        assert r["stuck"] == True
        assert r["action"] == "nudge"

        mark_stale(wiki)
        mark_stale(wiki)
        r = check_watchdog(wiki)
        assert r["stuck"] == True
        assert r["action"] == "flag"


def test_watchdog_detects_dead_run():
    with tempfile.TemporaryDirectory() as tmp:
        wiki = init_wiki(tmp)
        init_state(wiki, "test", 5)

        state = read_state(wiki)
        state["last_seen"] = time.time() - 8000
        (Path(tmp) / "state.json").write_text(json.dumps(state))

        r = check_watchdog(wiki)
        assert r["alive"] == False
        assert "restart" in r["action"]


def test_progress_resets_stale():
    """Progress should happen without incrementing stale count."""
    with tempfile.TemporaryDirectory() as tmp:
        wiki = init_wiki(tmp)
        init_state(wiki, "test", 5)
        mark_stale(wiki)

        update_state(wiki, add_extracted="entity-x")
        state = read_state(wiki)
        assert state["stale_count"] == 1  # unchanged


def test_watchdog_no_state():
    with tempfile.TemporaryDirectory() as tmp:
        wiki = init_wiki(tmp)
        r = check_watchdog(wiki)
        assert r["alive"] == False
        assert "no state" in r["reason"]


def test_state_tracks_last_seen():
    with tempfile.TemporaryDirectory() as tmp:
        wiki = init_wiki(tmp)
        t0 = time.time()
        init_state(wiki, "test", 5)
        mark_stale(wiki)
        state = read_state(wiki)
        assert state["last_seen"] is not None
        assert state["last_seen"] >= t0


def test_update_state_fields():
    with tempfile.TemporaryDirectory() as tmp:
        wiki = init_wiki(tmp)
        init_state(wiki, "doc", 10)
        update_state(wiki, chunk=3, add_extracted="entity-a")
        update_state(wiki, add_extracted="entity-b", add_touched="entity-a")

        state = read_state(wiki)
        assert state["chunk"] == 3
        assert state["extracted"] == ["entity-a", "entity-b"]
        assert state["pages_touched"] == ["entity-a"]
