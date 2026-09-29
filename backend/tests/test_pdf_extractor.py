"""Offline test for the extract step. It makes no network calls.

The seam is requests.get. We replace it with a fake that returns the small PDF in
tests/fixtures/, so the whole path from bytes to Paper Text runs without the network.
The line repair and the reference cut get their own tests, because that is where the
bugs live.
"""

from pathlib import Path

import pytest

from src.ingest import pdf_extractor
from tests.fixtures import make_sample_pdf
from src.ingest.pdf_extractor import (
    _cut_references,
    _normalize,
    _paragraphs,
    extract_paper_text,
)

SAMPLE = Path(__file__).parent / "fixtures" / "sample_paper.pdf"


class FakeResponse:
    """Stands in for the object requests.get returns."""

    def __init__(self, status_code, content):
        self.status_code = status_code
        self.content = content


def fake_get(response):
    """Build a replacement for requests.get that always returns `response`."""

    def get(url, timeout=None, headers=None):
        return response

    return get


def test_downloads_and_extracts_the_sample(monkeypatch):
    pdf_bytes = SAMPLE.read_bytes()
    monkeypatch.setattr(pdf_extractor.requests, "get", fake_get(FakeResponse(200, pdf_bytes)))

    text = extract_paper_text("https://example.test/paper.pdf")

    # The line break inside "feder-ated" is repaired.
    assert "federated learning" in text
    # The body survives.
    assert "does not yet handle clients" in text
    # The reference list and its heading are gone.
    assert "Smith, J. 2020" not in text
    assert "References" not in text


def test_raises_when_the_status_is_not_200(monkeypatch):
    monkeypatch.setattr(pdf_extractor.requests, "get", fake_get(FakeResponse(404, b"%PDF-1.4")))

    with pytest.raises(ValueError, match="status 404"):
        extract_paper_text("https://example.test/missing.pdf")


def test_raises_when_the_bytes_are_not_a_pdf(monkeypatch):
    # arXiv can answer 200 with an HTML error page. The bytes decide, not the headers.
    monkeypatch.setattr(
        pdf_extractor.requests, "get", fake_get(FakeResponse(200, b"<html>Rate limited</html>"))
    )

    with pytest.raises(ValueError, match="did not return a PDF"):
        extract_paper_text("https://example.test/error.pdf")


def test_keeps_a_real_hyphen_and_repairs_a_split_word():
    page = "\n".join(
        [
            "We compare our method against the Transformer-",
            "XL baseline, and we also study a second feder-",
            "ated setting with ten clients per round.",
            "Short close.",
        ]
    )

    joined = _paragraphs(page)

    # A capital after the hyphen means the hyphen is part of the name.
    assert "Transformer-XL" in joined
    # A lowercase letter after it means the line break split one word.
    assert "federated setting" in joined


def test_normalize_replaces_typesetting_characters():
    assert _normalize("the ﬁrst ‘result’ – here") == "the first 'result' - here"
    # An accented author name stays whole.
    assert _normalize("Aguèra") == "Aguèra"


def test_cut_references_keeps_everything_when_there_is_no_heading():
    text = "One paragraph.\n\nAnother paragraph."

    assert _cut_references(text) == text


def test_reads_a_two_column_page_one_column_at_a_time(monkeypatch):
    pdf_bytes = SAMPLE.read_bytes()
    monkeypatch.setattr(pdf_extractor.requests, "get", fake_get(FakeResponse(200, pdf_bytes)))

    text = extract_paper_text("https://example.test/paper.pdf")

    # Each column reads as one unbroken sentence. Read straight across the page, the two
    # columns interleave line by line and neither sentence survives.
    assert "The left column opens the section and runs for several lines" in text
    assert "The right column carries the rest of the same section" in text
    # The left column comes first.
    assert text.index("The left column") < text.index("The right column")


def test_cut_references_cuts_at_the_last_heading():
    # The word appears in the body too, so the first match is the wrong one.
    text = "\n".join(
        [
            "We follow the References section of the earlier survey.",
            "Our result holds.",
            "References",
            "Smith, J. 2020. Another paper.",
        ]
    )

    kept = _cut_references(text)

    assert "We follow the References section" in kept
    assert "Smith, J. 2020" not in kept


def test_raises_when_the_pdf_holds_no_text(monkeypatch):
    # A scanned paper holds pictures of words, so every page returns nothing. Silent
    # empty text would become a false Untouched Verdict later on.
    blank = make_sample_pdf.build([[(72, [])]])
    monkeypatch.setattr(pdf_extractor.requests, "get", fake_get(FakeResponse(200, blank)))

    with pytest.raises(ValueError, match="produced no text"):
        extract_paper_text("https://example.test/scan.pdf")
