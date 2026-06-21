"""Tests for autowiki core functions."""

import tempfile
from pathlib import Path
from autowiki.wiki import init_wiki, save_raw_source, check_drift, compute_sha256
from autowiki.ingest import chunk_text, detect_type, safe_filename
from autowiki.validate import validate_wiki, check_claim_fidelity, score_confidence
from autowiki.index import rebuild_index
from autowiki.query import search


def test_init_wiki():
    with tempfile.TemporaryDirectory() as tmp:
        wiki = init_wiki(tmp, domain="Test")
        assert (wiki / "SCHEMA.md").exists()
        assert (wiki / "index.md").exists()
        assert (wiki / "log.md").exists()
        assert (wiki / "entities").is_dir()
        assert (wiki / "concepts").is_dir()
        assert (wiki / "claims").is_dir()
        assert (wiki / "raw" / "articles").is_dir()

        # Verify SCHEMA content
        schema = (wiki / "SCHEMA.md").read_text()
        assert "Test" in schema


def test_save_raw_and_drift():
    with tempfile.TemporaryDirectory() as tmp:
        wiki = init_wiki(tmp)
        body = "This is a test document.\nWith multiple lines.\n"
        path = save_raw_source(wiki, body, source_url="test://example",
                               doc_type="article")

        # No drift initially
        assert not check_drift(path)

        # Modify the file
        path.write_text(path.read_text().replace("test", "modified"))
        assert check_drift(path)


def test_sha256_strip():
    """sha256 should strip whitespace (fix for file format newline bug)."""
    body = "hello world\n"
    sha = compute_sha256(body)
    sha_stripped = compute_sha256(body.strip())
    assert sha == sha_stripped


def test_chunk_text():
    text = "A" * 100 + "\n\n" + "B" * 100
    chunks = list(chunk_text(text, target_chars=50))
    assert len(chunks) >= 1


def test_chunk_log():
    log = "\n".join(f"line {i}" for i in range(100))
    chunks = list(chunk_text(log, target_chars=200))
    assert len(chunks) >= 1


def test_detect_type():
    assert detect_type(Path("test.py")) == "code"
    assert detect_type(Path("test.pdf")) == "paper"
    assert detect_type(Path("test.jsonl")) == "log"
    assert detect_type(Path("test.csv")) == "data"
    assert detect_type(Path("test.md")) == "article"


def test_safe_filename():
    assert safe_filename("Hello World!") == "hello-world"
    assert safe_filename("ENPIRE: Agentic Robot") == "enpire-agentic-robot"


def test_claim_fidelity():
    source = "The model achieves up to 95% accuracy on the test set."
    claim = "The model achieves 95% accuracy."
    result = check_claim_fidelity(claim, source)
    assert not result["faithful"]
    assert any("up to" in i.lower() for i in result["issues"])


def test_score_confidence():
    assert score_confidence(2, False, True) == "high"
    assert score_confidence(1, False, True) == "medium"
    assert score_confidence(2, True, True) == "low"
    assert score_confidence(2, False, False) == "low"
    assert score_confidence(2, False, True, is_opinion=True) == "low"


def test_validate_empty_wiki():
    with tempfile.TemporaryDirectory() as tmp:
        wiki = init_wiki(tmp)
        report = validate_wiki(wiki)
        assert report.total_pages == 0
        assert report.healthy


def test_search_empty():
    with tempfile.TemporaryDirectory() as tmp:
        wiki = init_wiki(tmp)
        results = search(wiki, "test")
        assert len(results) == 0
