"""Offline test for the pipeline step. It makes no network calls and writes no PDFs.

The seams are the `fetch`, `extract`, and `split` arguments of run_pipeline. We pass
fakes, so the test checks what the pipeline DOES with the three steps: which files it
writes, which papers it skips, and what it does when one paper raises.
"""

import json

from src.ingest.pipeline import run_pipeline


def fake_fetch(phrase, start, end, max_results=50):
    """Two Paper Records, in the shape fetch_papers returns."""

    return [
        {
            "arxiv_id": "1602.05629",
            "raw_id": "1602.05629",
            "version": "v1",
            "pdf_url": "https://arxiv.org/pdf/1602.05629v1",
            "title": "First Paper",
            "authors": ["Ada Lovelace"],
            "abstract": "An abstract.",
            "published": "2016-02-17T00:00:00+00:00",
            "primary_category": "cs.LG",
        },
        {
            "arxiv_id": "1610.05492",
            "raw_id": "1610.05492",
            "version": "v1",
            "pdf_url": "https://arxiv.org/pdf/1610.05492v1",
            "title": "Second Paper",
            "authors": ["Alan Turing"],
            "abstract": "Another abstract.",
            "published": "2016-10-18T00:00:00+00:00",
            "primary_category": "cs.LG",
        },
    ]


def fake_extract(pdf_url):
    return "One sentence. Two sentences."


def fake_split(text):
    return ["One sentence.", "Two sentences."]


def test_saves_three_files_per_paper(tmp_path):
    counts = run_pipeline(
        "Federated Learning",
        "2015-01-01",
        "2021-12-31",
        out_dir=tmp_path,
        fetch=fake_fetch,
        extract=fake_extract,
        split=fake_split,
    )

    assert counts["saved"] == 2
    assert counts["skipped"] == 0
    assert counts["failed"] == 0

    # The phrase became a safe directory name.
    paper_dir = tmp_path / "federated-learning" / "1602.05629"
    assert (paper_dir / "text.txt").read_text() == "One sentence. Two sentences."

    sentences = json.loads((paper_dir / "sentences.json").read_text())
    assert sentences == ["One sentence.", "Two sentences."]

    record = json.loads((paper_dir / "paper.json").read_text())
    assert record["title"] == "First Paper"
    assert record["sentence_count"] == 2
    # The collection date has to be on the record: an Untouched Verdict is only true
    # as of the day the Snapshot was gathered.
    assert "collected_on" in record


def test_second_run_skips_finished_papers(tmp_path):
    common = dict(
        out_dir=tmp_path, fetch=fake_fetch, extract=fake_extract, split=fake_split
    )
    run_pipeline("Federated Learning", "2015-01-01", "2021-12-31", **common)

    again = run_pipeline("Federated Learning", "2015-01-01", "2021-12-31", **common)
    assert again["skipped"] == 2
    assert again["saved"] == 0

    forced = run_pipeline(
        "Federated Learning", "2015-01-01", "2021-12-31", force=True, **common
    )
    assert forced["saved"] == 2
    assert forced["skipped"] == 0


def test_a_half_finished_paper_is_redone(tmp_path):
    """A run that died between two writes leaves a paper with some files, not all."""

    paper_dir = tmp_path / "federated-learning" / "1602.05629"
    paper_dir.mkdir(parents=True)
    (paper_dir / "text.txt").write_text("left over from a crashed run")

    counts = run_pipeline(
        "Federated Learning",
        "2015-01-01",
        "2021-12-31",
        out_dir=tmp_path,
        fetch=fake_fetch,
        extract=fake_extract,
        split=fake_split,
    )

    assert counts["saved"] == 2
    assert counts["skipped"] == 0
    assert (paper_dir / "text.txt").read_text() == "One sentence. Two sentences."


def test_one_bad_paper_does_not_end_the_run(tmp_path):
    def extract_that_fails_on_the_first_paper(pdf_url):
        if "1602.05629" in pdf_url:
            raise ValueError("probably a scanned paper")
        return "One sentence. Two sentences."

    counts = run_pipeline(
        "Federated Learning",
        "2015-01-01",
        "2021-12-31",
        out_dir=tmp_path,
        fetch=fake_fetch,
        extract=extract_that_fails_on_the_first_paper,
        split=fake_split,
    )

    assert counts["failed"] == 1
    # The second paper came after the failure, so this proves the run continued.
    assert counts["saved"] == 1
    assert not (tmp_path / "federated-learning" / "1602.05629").exists()
    assert (tmp_path / "federated-learning" / "1610.05492" / "paper.json").exists()


def test_fetch_gets_the_arguments_it_was_given(tmp_path):
    seen = {}

    def recording_fetch(phrase, start, end, max_results=50):
        seen.update(phrase=phrase, start=start, end=end, max_results=max_results)
        return []

    run_pipeline(
        "federated learning",
        "2015-01-01",
        "2021-12-31",
        max_results=7,
        out_dir=tmp_path,
        fetch=recording_fetch,
    )

    assert seen == {
        "phrase": "federated learning",
        "start": "2015-01-01",
        "end": "2021-12-31",
        "max_results": 7,
    }


def test_a_forced_run_that_fails_keeps_the_older_files(tmp_path, capsys):
    """Deleting them would lose a good paper to one timeout, so they stay and are named."""

    common = dict(
        out_dir=tmp_path, fetch=fake_fetch, extract=fake_extract, split=fake_split
    )
    run_pipeline("Federated Learning", "2015-01-01", "2021-12-31", **common)

    def extract_that_always_fails(pdf_url):
        raise ValueError("a timeout")

    counts = run_pipeline(
        "Federated Learning",
        "2015-01-01",
        "2021-12-31",
        force=True,
        out_dir=tmp_path,
        fetch=fake_fetch,
        extract=extract_that_always_fails,
        split=fake_split,
    )

    assert counts["failed"] == 2
    assert counts["saved"] == 0
    # The files from the first run are still there and still readable.
    paper_dir = tmp_path / "federated-learning" / "1602.05629"
    assert (paper_dir / "text.txt").read_text() == "One sentence. Two sentences."
    # And the run said so, so the age is not silent.
    assert "kept the older files" in capsys.readouterr().out
