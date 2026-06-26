import json
from pathlib import Path
import os
import pytest

from ingest.fetch_papers import fetch_arxiv_papers, enrich_with_semantic_scholar
from ingest import pipeline


REQUIRED_KEYS = {
    "arxiv_id",
    "title",
    "authors",
    "abstract",
    "published",
    "pdf_url",
    "primary_category",
    "citation_count",
    "s2_pdf_url",
}


def test_fetch_arxiv_papers_structure(mock_arxiv):
    fake_client, factory = mock_arxiv

    # Two styles of IDs: normal with version and old-style with slash
    r1 = factory("https://arxiv.org/abs/2005.11401v4")
    r2 = factory("https://arxiv.org/abs/cs/0612045v1")
    fake_client._results = [r1, r2]

    papers = fetch_arxiv_papers("retrieval augmented generation", max_results=2)

    assert isinstance(papers, list)
    assert len(papers) == 2
    for p in papers:
        assert isinstance(p, dict)
        assert REQUIRED_KEYS.issubset(p.keys())
        assert isinstance(p["authors"], list)
        assert all(isinstance(a, str) for a in p["authors"])


def test_arxiv_id_sanitization(mock_arxiv):
    fake_client, factory = mock_arxiv

    r1 = factory("https://arxiv.org/abs/2005.11401v4")
    r2 = factory("https://arxiv.org/abs/cs/0612045v1")
    fake_client._results = [r1, r2]

    papers = fetch_arxiv_papers("test", max_results=2)
    ids = [p["arxiv_id"] for p in papers]
    assert "2005.11401" in ids  # version suffix removed
    assert "cs_0612045" in ids  # slash replaced by underscore
    for pid in ids:
        assert "/" not in pid
        assert not pid.endswith(tuple(["v1", "v2", "v3"]))


def test_enrich_with_semantic_scholar(mock_semantic_scholar):
    # Prepare minimal papers list
    papers = [
        {"arxiv_id": "2005.11401", "title": "T", "authors": [], "abstract": "",
         "published": "2020-05-22T00:00:00+00:00", "pdf_url": "u", "primary_category": "cs.AI",
         "citation_count": None, "s2_pdf_url": None}
    ]

    enriched = enrich_with_semantic_scholar(papers)

    assert enriched[0]["citation_count"] == 42
    assert enriched[0]["s2_pdf_url"] == "https://example.org/open.pdf"


def test_pipeline_skips_existing(tmp_raw_dir, monkeypatch):
    # Arrange: create an existing file that would match the paper's arxiv_id
    existing_content = {"existing": True, "value": 123}
    paper = {
        "arxiv_id": "2601.12345",
        "title": "A Paper",
        "authors": ["A"],
        "abstract": "",
        "published": "2020-05-22T00:00:00+00:00",
        "pdf_url": "http://example/pdf",
        "primary_category": "cs.AI",
        "citation_count": 1,
        "s2_pdf_url": None,
    }

    path = tmp_raw_dir / f"{paper['arxiv_id']}.json"
    tmp_raw_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(existing_content))
    before = path.read_text()

    # Patch fetch functions to return just our paper and no network
    monkeypatch.setattr(pipeline, "fetch_arxiv_papers", lambda *a, **k: [paper])
    monkeypatch.setattr(pipeline, "enrich_with_semantic_scholar", lambda x: x)

    pipeline.run_ingestion(query="q", max_results=1, dry_run=False)

    after = path.read_text()
    assert after == before  # file not overwritten


def test_pipeline_dry_run_no_write(tmp_raw_dir, monkeypatch):
    paper = {
        "arxiv_id": "2602.55555",
        "title": "Dry Run",
        "authors": ["A"],
        "abstract": "",
        "published": "2020-05-22T00:00:00+00:00",
        "pdf_url": "http://example/pdf",
        "primary_category": "cs.AI",
        "citation_count": 0,
        "s2_pdf_url": None,
    }

    monkeypatch.setattr(pipeline, "fetch_arxiv_papers", lambda *a, **k: [paper])
    monkeypatch.setattr(pipeline, "enrich_with_semantic_scholar", lambda x: x)

    pipeline.run_ingestion(query="q", max_results=1, dry_run=True)

    # Directory should remain empty
    assert not tmp_raw_dir.exists() or len(list(tmp_raw_dir.glob("*.json"))) == 0


def test_pipeline_path_traversal_guard(tmp_raw_dir, monkeypatch):
    malicious = {
        "arxiv_id": "../evil",
        "title": "Malicious",
        "authors": [],
        "abstract": "",
        "published": "2020-05-22T00:00:00+00:00",
        "pdf_url": "http://example/pdf",
        "primary_category": "cs.AI",
        "citation_count": 0,
        "s2_pdf_url": None,
    }

    monkeypatch.setattr(pipeline, "fetch_arxiv_papers", lambda *a, **k: [malicious])
    monkeypatch.setattr(pipeline, "enrich_with_semantic_scholar", lambda x: x)

    pipeline.run_ingestion(query="q", max_results=1, dry_run=False)

    # Ensure nothing got written
    assert list(tmp_raw_dir.glob("*.json")) == []
