"""Step 01 of ingestion: ask arXiv for papers inside a date range.

Fynd compares a paper against later work across a cutoff date. So papers can never
arrive as one undated pile. The caller runs this twice: once ending at the cutoff, for
the papers that state open problems, and once starting at the cutoff, for the later
papers Refutation searches. The date range is the whole point of this step.
"""

import re
from datetime import datetime

import arxiv

PDF_BASE = "https://arxiv.org/pdf"

# One client for the whole program. The library waits 3 seconds between requests, and it
# counts that wait per client. A fresh client each call forgets the wait, and two calls
# back to back then break the arXiv request policy.
_CLIENT = arxiv.Client()


def _to_record(result) -> dict:
    """Turn one arXiv search result into a Paper Record (a plain dict)."""

    # result.entry_id looks like "http://arxiv.org/abs/2005.05265v2".
    # Take the part after "/abs/", then drop the trailing version.
    after_abs = result.entry_id.split("/abs/")[-1]
    raw_id = re.sub(r"v\d+$", "", after_abs)

    # Old ids such as "cs/0612045" contain a slash, which would make a directory
    # if we used it as a file name. So we keep two forms: one safe, one original.
    arxiv_id = raw_id.replace("/", "_")

    # Always v1. We never copy result.pdf_url, because that points at the newest
    # version, which can mention work published after the cutoff. That is a Leak.
    pdf_url = f"{PDF_BASE}/{raw_id}v1"

    return {
        "arxiv_id": arxiv_id,
        "raw_id": raw_id,
        "version": "v1",
        "pdf_url": pdf_url,
        "title": result.title,
        # result.authors holds Author objects, so we pull the name out of each one.
        "authors": [author.name for author in result.authors],
        "abstract": result.summary,
        # result.published is the FIRST submission date. result.updated is the date of
        # the newest version, and we drop it, because a v2 date can sit after the cutoff.
        "published": result.published.isoformat(),
        "primary_category": result.primary_category,
    }


def fetch_papers(
    phrase: str,
    start: str,
    end: str,
    max_results: int = 50,
    client=None,
) -> list[dict]:
    """Search arXiv abstracts for `phrase`, between the days `start` and `end`.

    Dates are plain strings such as "2019-01-01". Both days are included in full, so a
    2022-01-01 cutoff is written as end="2021-12-31". Returns a list of Paper Records.
    Writes no files: ticket 04 saves the Snapshot.
    """

    # A quote inside the phrase would close our own quote early and silently search for
    # something else. Better to stop than to return the wrong corpus.
    if '"' in phrase:
        raise ValueError("phrase must not contain a double quote")

    # Parse the dates instead of trusting them. "2019-1-1" cut up by hand gives a 10
    # character stamp where arXiv wants 12, and the date filter then fails quietly.
    # A quiet date failure in this file is exactly how post-cutoff papers leak in.
    start_day = datetime.strptime(start, "%Y-%m-%d").date()
    end_day = datetime.strptime(end, "%Y-%m-%d").date()

    # arXiv wants YYYYMMDDHHMM. We take the whole of the first day and the whole of the
    # last day, so a date the caller types means the day they meant.
    start_stamp = start_day.strftime("%Y%m%d") + "0000"
    end_stamp = end_day.strftime("%Y%m%d") + "2359"

    # No category limit on purpose: a Transfer Angle comes from another field.
    query = f'abs:"{phrase}" AND submittedDate:[{start_stamp} TO {end_stamp}]'

    search = arxiv.Search(
        query=query,
        max_results=max_results,
        # Relevance, not date, so 50 results are the 50 best matches in the window.
        sort_by=arxiv.SortCriterion.Relevance,
    )

    # The client is a seam: tests pass a fake one, so they never touch the network.
    if client is None:
        client = _CLIENT

    papers = []
    dropped = 0
    for result in client.results(search):
        # Check the window ourselves as well. arXiv filters on its own submittedDate
        # index, and we do not know its time zone, so a paper submitted hours from the
        # cutoff can come back on the wrong side. We own the cutoff, not arXiv.
        submitted = result.published.date()
        if submitted < start_day or submitted > end_day:
            dropped += 1
            continue
        papers.append(_to_record(result))

    # Fewer papers than asked for is a fact about the date window, not an error.
    print(f"Fetched {len(papers)} papers for '{phrase}' between {start} and {end}")
    if dropped:
        print(f"Dropped {dropped} papers that arXiv returned outside the window")
    if len(papers) == max_results:
        print(
            f"Hit the limit of {max_results}. The window holds more papers than this."
        )
    return papers
