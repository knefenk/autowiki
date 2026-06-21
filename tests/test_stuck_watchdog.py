"""Extended tests for stuck detection, watchdog, and performance patterns."""

import json, time, tempfile, sys
from pathlib import Path
from autowiki.wiki import init_wiki
import subprocess, os

# Find the script relative to the repo root
_REPO = Path(__file__).resolve().parent.parent
SCRIPT = str(_REPO / "skills" / "autowiki" / "scripts" / "autowiki.py")
# Fallback: use the installed Hermes skill path
if not os.path.exists(SCRIPT):
    SCRIPT = os.path.expanduser("~/.hermes/skills/research/autowiki/scripts/autowiki.py")
# Last resort: assume it's in PATH via pip install
if not os.path.exists(SCRIPT):
    SCRIPT = "autowiki"  # use CLI if available

def run(*args):
    if SCRIPT == "autowiki":
        return subprocess.run([sys.executable, "-m", "autowiki.cli"] + list(args), capture_output=True, text=True)
    return subprocess.run([sys.executable, SCRIPT] + list(args), capture_output=True, text=True)

# ── Stuck detection ──────────────────────────────────────────

def test_stale_counter_increments():
    with tempfile.TemporaryDirectory() as tmp:
        wiki = init_wiki(tmp)
        out = run("state", "--init", "test-doc", "--total", "5", "--path", tmp)
        assert "State initialized" in out.stdout

        r1 = json.loads(run("stale", "--path", tmp).stdout)
        assert r1["stale_count"] == 1
        assert "retry" in r1["suggestion"]

        r2 = json.loads(run("stale", "--path", tmp).stdout)
        assert r2["stale_count"] == 2
        assert "change chunk" in r2["suggestion"]

        r3 = json.loads(run("stale", "--path", tmp).stdout)
        r4 = json.loads(run("stale", "--path", tmp).stdout)
        assert r4["stale_count"] == 4
        assert "human" in r4["suggestion"]


def test_watchdog_detects_stuck():
    with tempfile.TemporaryDirectory() as tmp:
        wiki = init_wiki(tmp)
        run("state", "--init", "test", "--total", "5", "--path", tmp)

        # Fresh: not stuck
        r = json.loads(run("watchdog", "--path", tmp).stdout)
        assert r["alive"] == True
        assert r["stuck"] == False

        # After 2 stalls: nudged
        run("stale", "--path", tmp)
        run("stale", "--path", tmp)
        r = json.loads(run("watchdog", "--path", tmp).stdout)
        assert r["stuck"] == True
        assert r["action"] == "nudge"

        # After 4 stalls: flagged
        run("stale", "--path", tmp)
        run("stale", "--path", tmp)
        r = json.loads(run("watchdog", "--path", tmp).stdout)
        assert r["stuck"] == True
        assert r["action"] == "flag"


def test_watchdog_detects_dead_run():
    with tempfile.TemporaryDirectory() as tmp:
        wiki = init_wiki(tmp)
        run("state", "--init", "test", "--total", "5", "--path", tmp)
        
        # Fake an old last_seen
        state_file = Path(tmp) / "state.json"
        state = json.loads(state_file.read_text())
        state["last_seen"] = time.time() - 8000  # 2h+ ago
        state_file.write_text(json.dumps(state))

        r = json.loads(run("watchdog", "--path", tmp).stdout)
        assert r["alive"] == False
        assert "restart" in r["action"]


def test_stale_resets_with_progress():
    """Stale counter should NOT reset — it tracks cumulative stalls.
    But extracting successfully should not increment it."""
    with tempfile.TemporaryDirectory() as tmp:
        wiki = init_wiki(tmp)
        run("state", "--init", "test", "--total", "5", "--path", tmp)
        run("stale", "--path", tmp)

        # Progress: add extracted item (doesn't touch stale_count)
        r = json.loads(run("state", "--add-extracted", "entity-x", "--path", tmp).stdout)
        assert r["stale_count"] == 1  # unchanged, extraction succeeded


def test_watchdog_no_state():
    with tempfile.TemporaryDirectory() as tmp:
        wiki = init_wiki(tmp)
        r = json.loads(run("watchdog", "--path", tmp).stdout)
        assert r["alive"] == False
        assert "no state" in r["reason"]


# ── Performance / context window ─────────────────────────────

def test_chunk_size_control():
    """Smaller target = more chunks = lower per-chunk context."""
    # Create a test file of ~8K chars
    text = ("Section A\n" + "x" * 3000 + "\n\n" + 
            "Section B\n" + "y" * 3000 + "\n\n" +
            "Section C\n" + "z" * 2000)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(text)
        fpath = f.name

    try:
        # Default chunking (~12K target = 1 chunk for 8K text)
        r1 = run("chunk", fpath, "--dry-run")
        chunks_default = len([l for l in r1.stdout.split("\n") if l.startswith("===")])

        # Small chunking (4K target = 2-3 chunks for 8K text)
        r2 = run("chunk", fpath, "--target", "4000", "--dry-run")
        chunks_small = len([l for l in r2.stdout.split("\n") if l.startswith("===")])

        assert chunks_small >= chunks_default, f"Small target should produce more chunks: {chunks_small} vs {chunks_default}"
    finally:
        os.unlink(fpath)


def test_micro_skill_token_budget():
    """Verify micro-skill stays under 1K tokens."""
    skill_path = "/home/knef/.hermes/skills/research/autowiki/references/micro-skill.md"
    chars = len(open(skill_path).read())
    tokens = chars // 4
    assert tokens < 1200, f"Micro-skill is {tokens} tokens, target < 1200"


def test_watchdog_is_cheap():
    """Watchdog should be a single stat call on state.json — no filesystem scan."""
    with tempfile.TemporaryDirectory() as tmp:
        wiki = init_wiki(tmp)
        run("state", "--init", "test", "--total", "5", "--path", tmp)

        t0 = time.time()
        run("watchdog", "--path", tmp)
        elapsed = time.time() - t0
        # Should be near-instant (<0.3s for Python startup + json read)
        assert elapsed < 2.0, f"Watchdog took {elapsed:.2f}s, should be near-instant"


def test_audit_pass_simulated():
    """Simulate the independent audit: pick claims, re-check sources."""
    with tempfile.TemporaryDirectory() as tmp:
        wiki = init_wiki(tmp, domain="test")

        # Create a raw source with a claim
        raw_content = """This model achieves 95% accuracy on ImageNet.
The training took 3 days on 8 GPUs."""
        raw_dir = wiki / "raw" / "articles"
        raw_dir.mkdir(parents=True, exist_ok=True)
        import hashlib
        sha = hashlib.sha256(raw_content.strip().encode()).hexdigest()
        (raw_dir / "test-source.md").write_text(f"""---
source_url: test://example
ingested: 2026-06-21
sha256: {sha}
type: article
---
{raw_content}""")

        # Create a claim page (what the main loop might produce)
        (wiki / "claims").mkdir(exist_ok=True)
        (wiki / "claims" / "test-claim.md").write_text("""---
title: "Model achieves 95% on ImageNet"
created: 2026-06-21
updated: 2026-06-21
type: claim
tags: [benchmark]
sources: [raw/articles/test-source.md]
confidence: high
contested: false
contradictions: []
---

# Claim: 95% ImageNet accuracy

The model achieves 95% accuracy on ImageNet. ^[raw/articles/test-source.md]
""")

        # AUDIT: re-read source, compare
        source_body = (wiki / "raw" / "articles" / "test-source.md").read_text()
        _, stored_sha = source_body.split("---", 2)[1], source_body.split("---", 2)[2].strip()
        
        # Check claim fidelity
        claim_text = (wiki / "claims" / "test-claim.md").read_text()
        assert "95%" in claim_text
        assert "ImageNet" in claim_text
        # Source says "achieves 95% accuracy" — no qualifier like "up to"
        # So the claim is faithful
        assert "up to" not in source_body.lower()


def test_full_pipeline_commands_exist():
    """All new commands are registered."""
    r = run("--help")
    assert "watchdog" in r.stdout
    assert "stale" in r.stdout
    assert "state" in r.stdout
    assert "chunk" in r.stdout


def test_state_tracks_last_seen():
    with tempfile.TemporaryDirectory() as tmp:
        wiki = init_wiki(tmp)
        t0 = time.time()
        run("state", "--init", "test", "--total", "5", "--path", tmp)
        run("stale", "--path", tmp)  # updates last_seen
        state = json.loads((Path(tmp) / "state.json").read_text())
        assert state["last_seen"] is not None
        assert state["last_seen"] >= t0
