"""Offline test for the fetch step. It makes no network calls.

The seam is the `client` argument of fetch_papers. We pass a fake client, so we can
check both what the function SENDS to arXiv (the query) and what it RETURNS (the records).
"""

from datetime import datetime, timezone

from src.ingest.fetch_papers import fetch_papers, problem_keywords, search_later_papers


class FakeAuthor:
    # The real arxiv library gives Author objects, not strings. We copy that shape.
    def __init__(self, name):
        self.name = name


class FakeResult:
    """One arXiv search result, with only the attributes our code reads."""

    def __init__(self, entry_id, published, updated):
        self.entry_id = entry_id
        self.title = "A Title"
        self.authors = [FakeAuthor("Ada Lovelace")]
        self.summary = "An abstract."
        self.published = published
        self.updated = updated
        self.primary_category = "cs.LG"
        # The real library offers this, pointing at the NEWEST version. We must ignore it.
        self.pdf_url = entry_id.replace("/abs/", "/pdf/")


class FakeClient:
    """Stands in for arxiv.Client. It records the search it was given."""

    def __init__(self, results):
        self._results = results
        self.search = None  # filled in when results() is called

    def results(self, search):
        self.search = search
        return iter(self._results)


def make_client():
    published = datetime(2020, 5, 11, 17, 7, 40, tzinfo=timezone.utc)
    updated = datetime(2020, 5, 12, 13, 1, 54, tzinfo=timezone.utc)
    return FakeClient([
        # A new style id, returned as v2 by arXiv.
        FakeResult("http://arxiv.org/abs/2005.05265v2", published, updated),
        # An old style id, which contains a slash.
        FakeResult("http://arxiv.org/abs/cs/0612045v1", published, updated),
    ])


def test_new_style_id_gets_a_v1_pdf_link():
    client = make_client()
    papers = fetch_papers("federated learning", "2019-01-01", "2021-12-31", client=client)

    paper = papers[0]
    assert paper["raw_id"] == "2005.05265"
    assert paper["arxiv_id"] == "2005.05265"
    assert paper["version"] == "v1"
    # Not v2, even though arXiv returned v2. A later version is a Leak.
    assert paper["pdf_url"] == "https://arxiv.org/pdf/2005.05265v1"


def test_old_style_id_is_safe_as_a_file_name_but_the_link_keeps_the_slash():
    client = make_client()
    papers = fetch_papers("federated learning", "2019-01-01", "2021-12-31", client=client)

    paper = papers[1]
    assert paper["raw_id"] == "cs/0612045"
    assert paper["arxiv_id"] == "cs_0612045"
    assert paper["pdf_url"] == "https://arxiv.org/pdf/cs/0612045v1"


def test_the_first_submission_date_is_kept_and_the_update_date_is_dropped():
    client = make_client()
    papers = fetch_papers("federated learning", "2019-01-01", "2021-12-31", client=client)

    paper = papers[0]
    assert paper["published"] == "2020-05-11T17:07:40+00:00"
    # The 2020-05-12 update date must not reach any field.
    assert "2020-05-12" not in str(paper)


def test_dates_become_whole_days_in_the_query():
    client = make_client()
    fetch_papers("federated learning", "2019-01-01", "2021-12-31", client=client)

    query = client.search.query
    assert "submittedDate:[201901010000 TO 202112312359]" in query


def test_the_phrase_is_quoted_and_searched_in_the_abstract():
    client = make_client()
    fetch_papers("federated learning", "2019-01-01", "2021-12-31", client=client)

    assert 'abs:"federated learning"' in client.search.query


def test_a_date_without_padding_still_makes_a_correct_stamp():
    # Parsing repairs "2019-1-1". Cutting the string up by hand would give a 10
    # character stamp, and arXiv would then ignore the date filter.
    client = make_client()
    fetch_papers("federated learning", "2019-1-1", "2021-12-31", client=client)

    assert "submittedDate:[201901010000 TO 202112312359]" in client.search.query


def test_a_date_in_the_wrong_format_raises():
    client = make_client()
    try:
        fetch_papers("federated learning", "01/01/2019", "2021-12-31", client=client)
    except ValueError:
        pass
    else:
        raise AssertionError("a date in the wrong format must raise")


def test_a_phrase_with_a_quote_raises():
    client = make_client()
    try:
        fetch_papers('the "hard" problem', "2019-01-01", "2021-12-31", client=client)
    except ValueError:
        pass
    else:
        raise AssertionError("a quote in the phrase must raise")


def test_a_paper_outside_the_window_is_dropped():
    # arXiv filters on its own index. If it hands back a 2022 paper for a window that
    # ends in 2021, we drop it ourselves, because that paper is a Leak.
    published = datetime(2022, 3, 1, tzinfo=timezone.utc)
    client = FakeClient([FakeResult("http://arxiv.org/abs/2203.00001v1", published, published)])

    papers = fetch_papers("federated learning", "2019-01-01", "2021-12-31", client=client)

    assert papers == []


# --- search_later_papers: the Phase 0 retrieval for one problem ---

PROBLEM = (
    "For future work, we will extend FedKT to the cross-device setting, where the "
    "number of parties is large and the data size of each party is small."
)


def test_keywords_drop_the_cue_and_the_grammar():
    words = problem_keywords(PROBLEM)

    # The subject matter survives.
    assert "fedkt" in words
    assert "cross-device" in words
    # The announcement and the grammar do not.
    assert "future" not in words
    assert "extend" not in words
    assert "where" not in words


def test_a_sentence_with_no_subject_matter_gives_no_keywords():
    # "We leave this to future work" names no problem, so there is nothing to search.
    assert problem_keywords("We leave this to future work.") == []


def test_the_query_asks_for_any_keyword_after_the_cutoff():
    client = make_client()
    search_later_papers(PROBLEM, "2022-01-01", client=client)

    query = client.search.query
    assert 'abs:"fedkt"' in query
    assert " OR " in query
    assert " AND " in query
    assert "submittedDate:[202201010000 TO " in query


def test_a_problem_with_no_keywords_sends_no_search():
    client = make_client()

    papers = search_later_papers("We leave this to future work.", "2022-01-01", client=client)

    assert papers == []
    assert client.search is None


def test_a_paper_from_before_the_cutoff_is_dropped():
    # A paper on this side of the cutoff is not later work, so judging it as later work
    # would be a Leak backwards.
    old = datetime(2021, 3, 1, tzinfo=timezone.utc)
    new = datetime(2023, 3, 1, tzinfo=timezone.utc)
    client = FakeClient([
        FakeResult("http://arxiv.org/abs/2103.00001v1", old, old),
        FakeResult("http://arxiv.org/abs/2303.00001v1", new, new),
    ])

    papers = search_later_papers(PROBLEM, "2022-01-01", client=client)

    assert [paper["arxiv_id"] for paper in papers] == ["2303.00001"]


def test_the_domain_phrase_is_required_in_the_abstract():
    client = make_client()
    search_later_papers(PROBLEM, "2022-01-01", domain="federated learning", client=client)

    assert client.search.query.startswith('abs:"federated learning" AND (')


# --- the four cases the code review found ---

def test_an_acronym_survives():
    # A floor of four letters deleted GAN, RNN, SGD, and IID, which is where the subject
    # matter of this field lives.
    words = problem_keywords("We leave the extension of our GAN to RNN encoders as an open problem.")

    assert "gan" in words
    assert "rnn" in words


def test_a_cue_inside_a_longer_word_is_left_alone():
    # "future work" sits inside "future workloads". A plain replace left "loads" behind.
    words = problem_keywords("We leave the handling of future workloads to later study.")

    assert "workloads" in words
    assert "loads" not in words


def test_two_overlapping_cues_leave_nothing_behind():
    # "open problem" sits inside "remains an open problem". Taking the short cue first
    # left "remains" as a keyword, and the long one leaves "problem".
    words = problem_keywords("How to choose the clipping norm remains an open problem in our setting.")

    assert "remains" not in words
    assert "problem" not in words
    assert "clipping" in words


def test_a_dropped_paper_is_said_out_loud(capsys):
    # We ask for exactly max_results and filter afterwards, so a silent drop reads as
    # "nobody addressed this problem".
    old = datetime(2021, 3, 1, tzinfo=timezone.utc)
    client = FakeClient([FakeResult("http://arxiv.org/abs/2103.00001v1", old, old)])

    search_later_papers(PROBLEM, "2022-01-01", client=client)

    assert "Dropped 1 papers submitted before the cutoff" in capsys.readouterr().out
