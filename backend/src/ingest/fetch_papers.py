"""Step 01 of ingestion: ask arXiv for papers inside a date range.

Fynd compares a paper against later work across a cutoff date. So papers can never
arrive as one undated pile. The caller runs this twice: once ending at the cutoff, for
the papers that state open problems, and once starting at the cutoff, for the later
papers Refutation searches. The date range is the whole point of this step.
"""

import re
from datetime import datetime, timezone

import arxiv

from src.ingest.problem_extractor import CUES

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


# Words that carry no subject matter. A problem sentence is written in prose, so most of
# it is grammar. Searching with these words returns the whole of arXiv.
#
# The last three lines matter for a different reason. Two cue phrases can overlap, as in
# "remains an open problem", where removing the longer cue leaves "problem" behind. And a
# citation inside the sentence leaves "et" and "al". Neither is subject matter.
_STOPWORDS = frozenset(
    """a an the and or but if then than that this these those there here where when
    which who whom whose what how why while with without within from into onto for
    of in on at by to as is are was were be been being do does did done have has had
    will would can could may might must shall should not no nor so such own same
    other others more most less least much many few several both each every all any
    some one two three also only just still yet however moreover thus therefore since
    because due about over under between among during after before above below again
    further our ours we us they them their it its his her he she you your i me my
    work plan plans future paper papers study studies approach method methods
    results result section sections leave leaves leaving extend extends extending
    use uses using used address addresses addressing
    problem problems challenge challenges issue issues question questions
    direction directions limitation limitations scope
    et al etc up vs via per ie eg cf""".split()
)

# How many words of the problem sentence reach the query. Past about eight, the extra
# words are the common ones, and they only pull the ranking toward unrelated papers.
_MAX_KEYWORDS = 8


def problem_keywords(sentence: str, limit: int = _MAX_KEYWORDS) -> list[str]:
    """Pick the subject matter words out of one Author-Stated Open Problem.

    The cue phrases go first. "For future work, we will extend FedKT to the cross-device
    setting" announces a problem with its first four words and names the problem with the
    rest, and the announcement is the same in every paper, so it is noise in a search.
    """

    lowered = sentence.lower()
    # Whole words only. "future work" sits inside "future workloads", and a plain replace
    # leaves "loads" behind as a keyword.
    # Longest cue first. "open problem" sits inside "remains an open problem", and taking
    # the short one first leaves "remains" behind as subject matter.
    for cue in sorted(CUES, key=len, reverse=True):
        lowered = re.sub(rf"\b{re.escape(cue)}\b", " ", lowered)

    kept = []
    # Two letters, not four. A floor of four deletes GAN, RNN, SGD, LLM, DP, and IID,
    # which is where the subject matter of this field lives. The stopword list above is
    # what removes the short grammar words.
    # Hyphens stay: "cross-device" is one term, and splitting it loses the term.
    for word in re.findall(r"[a-z][a-z-]+", lowered):
        word = word.strip("-")
        if word in _STOPWORDS or word in kept:
            continue
        kept.append(word)
        if len(kept) >= limit:
            break
    return kept


def search_later_papers(
    sentence: str,
    cutoff: str,
    max_results: int = 3,
    domain: str | None = None,
    client=None,
) -> list[dict]:
    """Find the later papers most likely to have addressed one problem.

    `cutoff` is a day such as "2022-01-01", and only papers first submitted on that day
    or after it come back. Returns at most `max_results` Paper Records, best match first.
    Writes no files.

    `domain` is the phrase of the Seeded Domain, such as "federated learning". Every
    returned paper must carry it in the abstract. Measured on one real problem: without
    it, two of the three results were about quantum entanglement and about apportionment,
    because a bag of words ranked them on "number", "large", and "size". It narrows
    Refutation to one field, which a Transfer Angle from another field would need, and
    Phase 0 does not produce Angles.

    This is the whole of retrieval in Phase 0, and arXiv's own relevance ranking is doing
    it. Phase 0 is therefore not evidence about retrieval. Phase 1 replaces this with
    embeddings and measures recall of the solving paper on its own.
    """

    keywords = problem_keywords(sentence)
    if not keywords:
        # No subject matter words means no search worth sending. Returning nothing is
        # honest; a query of stopwords would return arXiv's most popular papers.
        print(f"No keywords in: {sentence[:60]}...")
        return []

    cutoff_day = datetime.strptime(cutoff, "%Y-%m-%d").date()
    start_stamp = cutoff_day.strftime("%Y%m%d") + "0000"
    # UTC, not the local clock. arXiv indexes submission dates in its own zone, and a
    # machine behind UTC in the evening would cut off the newest day of papers, which is
    # the day most likely to hold the solving paper.
    end_stamp = datetime.now(timezone.utc).strftime("%Y%m%d") + "2359"

    # OR, not AND. Eight words joined by AND describe one paper, and usually that paper
    # is the source paper itself. OR asks arXiv to rank by how many of the words a later
    # paper matches, which is the question we are actually asking.
    # ponytail: bag of words over abstracts, no synonyms and no phrases. Phase 1 replaces
    # it with embeddings and measures recall of the solving paper.
    terms = " OR ".join(f'abs:"{word}"' for word in keywords)
    query = f"({terms}) AND submittedDate:[{start_stamp} TO {end_stamp}]"
    if domain:
        if '"' in domain:
            raise ValueError("domain must not contain a double quote")
        query = f'abs:"{domain}" AND {query}'

    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance,
    )

    if client is None:
        client = _CLIENT

    papers = []
    dropped = 0
    for result in client.results(search):
        # Own the cutoff here too. arXiv filters on its own index in a time zone we do
        # not know, and a paper from before the cutoff on this side is a Leak backwards:
        # it would be judged as later work when it is not.
        if result.published.date() < cutoff_day:
            dropped += 1
            continue
        papers.append(_to_record(result))

    print(f"Found {len(papers)} later papers for: {' '.join(keywords)}")
    # Say this out loud. We ask for exactly max_results and filter afterwards, so a
    # silent drop leaves a problem with no candidates, and an empty candidate list reads
    # as "nobody addressed this problem" when it means "we dropped them".
    if dropped:
        print(f"Dropped {dropped} papers submitted before the cutoff {cutoff}")
    return papers
