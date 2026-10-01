"""Offline test for the problem extraction step. It reads no files and calls no model.

The seam is `extract_problems(sentences, paper_id)`. A test hands it a list of sentences,
the same shape step 03 returns, and reads back the candidates.

The sentences quoted here are real. They come from the five federated learning papers of
the Phase 0 Snapshot, and the ticket records where each one was found.
"""

from src.ingest.problem_extractor import extract_problems

# 2010.01017, sentence 306. A real Author-Stated Open Problem: the authors name what their
# own method does not cover, and the setting it fails in.
REAL_PROBLEM = (
    "For future work, we will extend FedKT to the cross-device setting, where the number "
    "of parties is large and the data size of each party is small."
)


def test_finds_a_problem_the_author_states_about_their_own_work():
    sentences = ["We report one result.", REAL_PROBLEM, "We thank Wei Wang."]

    found = extract_problems(sentences, "2010.01017")

    assert len(found) == 1
    assert found[0]["paper_id"] == "2010.01017"
    assert found[0]["index"] == 1
    assert found[0]["problem"] == REAL_PROBLEM
    # The sentence alone can be meaningless, so its neighbours travel with it.
    assert found[0]["before"] == "We report one result."
    assert found[0]["after"] == "We thank Wei Wang."


def test_rejects_a_cue_sentence_with_no_actor():
    """2007.00914, sentence 83. A table of contents line, and the only false hit the
    drafted cue list produced across 2787 real sentences.

    It holds "future work" and states no problem. Both real hits carry a first person verb,
    and this one carries no actor at all, so a first person word is what separates them.
    """

    table_of_contents = (
        "Finally, the concluding remarks and future work 4 are described in Section 7."
    )

    assert extract_problems([table_of_contents], "2007.00914") == []


def test_a_problem_at_the_very_start_has_no_sentence_before_it():
    found = extract_problems([REAL_PROBLEM, "We thank Wei Wang."], "2010.01017")

    assert found[0]["before"] is None
    assert found[0]["after"] == "We thank Wei Wang."


def test_a_problem_at_the_very_end_has_no_sentence_after_it():
    found = extract_problems(["We report one result.", REAL_PROBLEM], "2010.01017")

    assert found[0]["before"] == "We report one result."
    assert found[0]["after"] is None


def test_ordinary_prose_yields_nothing():
    """2005.05265, sentence 0 onward. A paper that states no problem returns an empty list
    rather than raising, because most sentences of most papers are not problems."""

    sentences = [
        "Federated learning becomes increasingly attractive in wireless communications.",
        "In this article, we provide an overview of the relationship between the two.",
    ]

    assert extract_problems(sentences, "2005.05265") == []


def test_returns_every_candidate_in_the_order_they_are_printed():
    """2010.01017 gives two problems, at sentences 240 and 306. Nothing is capped or ranked,
    because a person picks ten problems by hand in ticket 03."""

    second = (
        "As future work, we plan to use the smooth sensitivity algorithm to add noises to "
        "the privacy losses."
    )
    sentences = ["Filler.", second, "Filler.", REAL_PROBLEM]

    found = extract_problems(sentences, "2010.01017")

    assert [candidate["index"] for candidate in found] == [1, 3]


# Real sentences from the two survey papers of the Snapshot. Each one carries a cue and a
# first person word, and none states a problem. The author is announcing that the paper
# contains a discussion of open problems, so the sentence is a pointer and not a claim.
POINTERS = [
    # 1907.09693, sentence 234.
    "In this section, we compare the existing FLSs according to the dimensions considered "
    "in Section 4 and present interesting future research directions.",
    # 1907.09693, sentence 96.
    "With these findings, we analyze the existing FLSs and figure out the potential future "
    "directions of FLSs in the following sections.",
    # 2005.05265, sentence 7.
    "We also identify some future research challenges and directions at the end of this "
    "article.",
    # 2009.13012, sentence 968.
    "This section presents various open challenges that exist in enabling federated "
    "learning over IoT networks.",
]


def test_rejects_a_sentence_that_only_points_at_a_discussion_of_problems():
    for pointer in POINTERS:
        assert extract_problems([pointer], "1907.09693") == [], pointer


def test_finds_a_plan_stated_without_the_words_future_work():
    """2007.00914, sentence 817. Found by the bounded read of the last thirty sentences, and
    missed by the first cue list, which knew "future work" but not "we plan to".

    It is a real Author-Stated Open Problem. The authors name what their own framework does
    not do yet, and they are the ones who would do it.
    """

    missed = (
        "Since FL and DP fields are constantly growing, we plan to extend the framework's "
        "functionalities by new federated aggregation operators, machine learning models, "
        "and data distributions."
    )

    found = extract_problems([missed], "2007.00914")

    assert len(found) == 1
    assert found[0]["index"] == 0
