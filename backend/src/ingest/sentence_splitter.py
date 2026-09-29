"""Step 03 of ingestion: cut Paper Text into sentences.

An Author-Stated Open Problem is one sentence. An author writes "our method does not yet
handle clients that leave in the middle of a training round", and that single sentence is
the unit Fynd extracts, searches against, and later quotes back to a student. A paper
held as one 38,000 character string has no units in it. This step makes them.
"""

import re

# Words that end in a period without ending a sentence. Measured in one real paper: 29
# uses of "et al.", 7 of "e.g.", and 2 of "vs.", against 243 places where a period is
# followed by a space. The rest are the obvious neighbours of those three.
#
# Case matters here. "No." is a number, as in "No. 5", but "no." at the end of a
# sentence is an ordinary word, and folding the case would glue that sentence to the
# next one.
ABBREVIATIONS = {
    "al",
    "e.g",
    "i.e",
    "vs",
    "cf",
    "Fig",
    "Eq",
    "Sec",
    "No",
    "Dr",
    "Prof",
}

# Marks that can sit after a sentence ends, such as the quote in: he said "no." Then...
CLOSERS = "\"')]"

# A sentence ends at a period, a question mark, or an exclamation mark, then any closing
# quote or bracket, then a space, then a capital letter or an opening bracket. A decimal
# number such as 0.85 needs no rule of its own, because it has no space after the period.
#
# (?<=...) means "with this just behind", and (?=...) means "with this just ahead".
# Neither is part of the match, so the split lands on the spaces alone.
# ponytail: a small rule list, not a trained model. Swap in pysbd if the output of a
# real paper ever reads wrong.
SENTENCE_END = re.compile(r"(?<=[.?!])([\"')\]]*)\s+(?=[A-Z(\[])")


def _ends_a_sentence(head: str) -> bool:
    """Say whether a block of text that ends at a candidate mark is a whole sentence."""

    words = head.split()
    if not words:
        return True

    # Take the last word bare: no brackets or quotes around it, no marks after it. So
    # "(e.g." becomes "e.g", and 'this."' becomes "this".
    word = words[-1].lstrip("(\"'[").rstrip(".?!" + CLOSERS)

    # A single letter is an initial, as in "H. Brendan McMahan".
    if len(word) == 1 and word.isalpha():
        return False

    return word not in ABBREVIATIONS


def _blocks(text: str) -> list[str]:
    """Split the text on blank lines, joining the blocks a sentence runs across."""

    blocks = []
    for block in text.split("\n\n"):
        block = " ".join(block.split())
        if not block:
            continue

        # Step 02 puts a blank line between pages, and a sentence often straddles one.
        # Without this join, every page break costs one real sentence, cut in half
        # exactly where a Limitations passage can sit.
        # A closing quote or bracket can sit after the final mark, as in: ...round."
        finished = blocks and blocks[-1].rstrip(CLOSERS).endswith((".", "?", "!"))

        # The next page can pick the sentence up at a digit, as in: ...fails in 2 of...
        carries_on = blocks and not finished and (block[0].islower() or block[0].isdigit())
        if carries_on:
            blocks[-1] = blocks[-1] + " " + block
        else:
            blocks.append(block)

    return blocks


def split_sentences(text: str) -> list[str]:
    """Turn the Paper Text of one paper into its sentences, in order."""

    sentences = []
    for block in _blocks(text):
        start = 0
        for mark in SENTENCE_END.finditer(block):
            # The closing quote or bracket belongs to the sentence that ends, not to the
            # gap between the two, so the head runs to the end of that group.
            head = block[start : mark.end(1)]
            if not _ends_a_sentence(head):
                continue
            sentences.append(head.strip())
            start = mark.end()

        # Whatever follows the last mark is the final sentence of the block. Nothing is
        # dropped for being short: filtering belongs in Phase 1, where each sentence
        # costs money, and where a wrong rule can be undone.
        tail = block[start:].strip()
        if tail:
            sentences.append(tail)

    # Step 02 raises for a paper that produced no text, so no text here means the split
    # itself lost the paper. Empty output read as a paper is a false Untouched Verdict
    # later on, the same failure one step earlier.
    if not sentences:
        raise ValueError("The text produced no sentences")

    print(f"Split into {len(sentences)} sentences")
    return sentences


if __name__ == "__main__":
    # The paper that named federated learning, read through step 02 first.
    from src.ingest.pdf_extractor import extract_paper_text

    sentences = split_sentences(extract_paper_text("https://arxiv.org/pdf/1602.05629v1"))
    print("--- the last 5 ---")
    for sentence in sentences[-5:]:
        print(f"  {sentence}")
