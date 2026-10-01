"""Offline test for the sentence split step. It makes no network calls.

The function is a pure one: text in, sentences out. So the test is the hard paragraph
from the ticket, held here as a string.
"""

import pytest

from src.ingest.sentence_splitter import split_sentences


def test_keeps_a_citation_whole():
    text = "We follow McMahan et al. 2016 in this setup. The result holds."

    assert split_sentences(text) == [
        "We follow McMahan et al. 2016 in this setup.",
        "The result holds.",
    ]


def test_keeps_an_abbreviation_whole():
    text = "Some clients drop out, e.g. Phones that lose signal. We handle that."

    assert split_sentences(text) == [
        "Some clients drop out, e.g. Phones that lose signal.",
        "We handle that.",
    ]


def test_keeps_a_decimal_number_whole():
    # There is no space after the period, so the split rule never fires here.
    text = "Accuracy reached 0.85 on the held out set. We report the mean."

    assert split_sentences(text) == [
        "Accuracy reached 0.85 on the held out set.",
        "We report the mean.",
    ]


def test_keeps_an_initial_whole():
    text = "The work of H. Brendan McMahan describes this. We build on it."

    assert split_sentences(text) == [
        "The work of H. Brendan McMahan describes this.",
        "We build on it.",
    ]


def test_joins_a_sentence_carried_across_a_page_break():
    # Step 02 puts a blank line between pages. A sentence often straddles one.
    text = "Our method does not yet handle clients that leave in\n\nthe middle of a round."

    assert split_sentences(text) == [
        "Our method does not yet handle clients that leave in the middle of a round."
    ]


def test_keeps_two_finished_paragraphs_apart():
    text = "The first paragraph ends here.\n\nThe second one starts here."

    assert split_sentences(text) == [
        "The first paragraph ends here.",
        "The second one starts here.",
    ]


def test_keeps_a_short_fragment():
    # Nothing is dropped for being short. Filtering belongs in Phase 1, where each
    # sentence costs money, not here, where dropping cannot be undone.
    text = "Introduction\n\nWe report one result."

    assert split_sentences(text) == ["Introduction", "We report one result."]


def test_splits_after_a_plain_no():
    # "No." is a number, as in "No. 5", but "no." is an ordinary word. The abbreviation
    # list matches case for exactly this reason.
    assert split_sentences("The answer is no. We move on.") == [
        "The answer is no.",
        "We move on.",
    ]


def test_keeps_a_numbered_item_whole():
    assert split_sentences("We use dataset No. 5 for this run.") == [
        "We use dataset No. 5 for this run."
    ]


def test_splits_after_a_closing_quote():
    # Step 02 turns curly quotes into plain ones, so this shape is common.
    text = 'The authors say "we do not handle this." The next paper does.'

    assert split_sentences(text) == [
        'The authors say "we do not handle this."',
        "The next paper does.",
    ]


def test_joins_a_page_break_that_continues_at_a_digit():
    text = "The method fails in\n\n2 of the twelve runs."

    assert split_sentences(text) == ["The method fails in 2 of the twelve runs."]


def test_raises_when_there_are_no_sentences():
    # Empty output read as a paper is a false Untouched Verdict later on.
    with pytest.raises(ValueError, match="no sentences"):
        split_sentences("   \n\n   ")


def test_splits_after_a_question_that_ends_in_a_variable():
    # "x" is one letter, so the initial rule used to swallow the question mark and join
    # the question to its answer. Only a period is ambiguous.
    sentences = split_sentences("What is the value of x? We show that it is small.")

    assert sentences == ["What is the value of x?", "We show that it is small."]


def test_keeps_a_heading_apart_from_the_paragraph_below_it():
    # A heading ends with no mark, so it looks unfinished. It is not joined, because the
    # next block starts with a capital. This is the rule that makes an uppercase
    # continuation across a page break stay split, and it is the safer trade.
    sentences = split_sentences("I. INTRODUCTION\n\nFederated learning trains a model.")

    assert sentences == ["I. INTRODUCTION", "Federated learning trains a model."]
