"""Step 05 of ingestion: find the sentences where an author states an open problem.

Everything downstream of here is one sentence wide. Refutation searches with the problem
sentence, the judge reads it, and the Research Brief quotes it back to a student. A paper
on disk is a list of 300 to 1100 sentences, and about two of them are what Fynd wants.

A heading cannot do this job. OBS-001 in `docs/v1-implementation-notes.md` measured 40
papers and found zero with a Limitations or a Future Work heading, so the sentence is the
only unit available.
"""

# Phrases an author uses when saying something is unsolved. Measured against the five
# papers of the Phase 0 Snapshot: a list holding only "future work" found 3 sentences in
# 2787 and missed 2005.05265 completely, because that paper writes "future research
# challenges". So the list carries the phrasings authors actually use.
CUES = (
    "does not yet",
    "do not yet",
    "cannot currently",
    "is not able to",
    "a limitation of",
    "one limitation",
    "limitations of our",
    "future work",
    "future research",
    "future direction",
    "open problem",
    "open challenge",
    "open issue",
    "we leave",
    "remains an open",
    "remains unsolved",
    "is still an open",
    "we did not address",
    "is beyond the scope",
    "we have not",
    # Found by the bounded read of 2007.00914, sentence 817: "we plan to extend the
    # framework's functionalities". A real problem, and the list above misses it, because the
    # author states the plan without ever writing "future work".
    "we plan to",
    "we intend to",
)


# Words that name the author as the actor. A cue alone is not enough. "Finally, the
# concluding remarks and future work 4 are described in Section 7" is a table of contents
# line, and it was the one false hit the cue list produced across 2787 real sentences. Both
# real hits carry a first person verb: "we will extend FedKT" and "we plan to use".
#
# This also keeps a survey's open challenges out. A survey states problems of the whole
# field, 55 of them in 2009.13012, and none is a limit of work its authors did. Corroboration
# counts how many separate groups name a problem, so one survey offering 55 would distort it,
# and an Angle needs a Reported Limitation, which assumes somebody tried and hit a limit.
ACTORS = ("we ", "we'", "our ", "us ", "ours ")

# Verbs an author uses to say what the paper itself contains. Measured on the five papers:
# the actor rule alone returned 8 candidates and 6 were sentences like "we present
# interesting future research directions" or "this section presents various open
# challenges". In every one of the six, a verb below sits in front of the cue. The author is
# pointing at a discussion of problems, not stating one. In both real problems the cue opens
# the sentence and nothing like this comes before it.
POINTING_VERBS = (
    "present",
    "provide",
    "identify",
    "analyze",
    "analyse",
    "compare",
    "discuss",
    "describe",
    "summarize",
    "summarise",
    "review",
    "outline",
    "figure out",
)


def _has_an_actor(lowered: str) -> bool:
    """Say whether the sentence names the author as the one who did the work."""

    # A leading space is added so "our" does not match inside "flourish", and the sentence
    # start is covered by the same test.
    padded = " " + lowered
    return any(actor in padded for actor in ACTORS)


def _only_points_at_a_discussion(lowered: str, cue: str) -> bool:
    """Say whether the sentence announces a discussion of problems instead of stating one."""

    before_the_cue = lowered[: lowered.index(cue)]
    return any(verb in before_the_cue for verb in POINTING_VERBS)


def extract_problems(sentences: list[str], paper_id: str) -> list[dict]:
    """Return the sentences of one paper where the author states an open problem.

    Each candidate carries the sentence, where it was found, and its neighbours, because
    a sentence such as "this remains an open question" carries no meaning alone.
    """

    found = []
    for index, sentence in enumerate(sentences):
        lowered = sentence.lower()

        # The first cue in the sentence, so the pointing test below knows where to look.
        cue = next((cue for cue in CUES if cue in lowered), None)
        if cue is None:
            continue
        if not _has_an_actor(lowered):
            continue
        if _only_points_at_a_discussion(lowered, cue):
            continue

        found.append(
            {
                "paper_id": paper_id,
                "index": index,
                "problem": sentence,
                "before": sentences[index - 1] if index > 0 else None,
                "after": sentences[index + 1] if index + 1 < len(sentences) else None,
            }
        )

    return found
