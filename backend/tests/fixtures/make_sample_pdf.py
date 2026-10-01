"""Write the small PDF that test_pdf_extractor.py reads.

A real arXiv PDF is about one megabyte, which is too big to keep in the repository, so
the test uses this one instead. Run this file only when the sample needs to change:

    python tests/fixtures/make_sample_pdf.py

A page here is a list of columns, and a column is a left edge and its printed lines.
One line in the list is one printed line, the way a PDF stores text. A column may carry
a third item, "sideways", which prints it rotated a quarter turn, the way arXiv stamps
its own identifier down the left edge of page one.
"""

from pathlib import Path

# Page one is a single column. The long lines are the body of a paragraph and the short
# line ends it. "feder-" and "ated" test the hyphen repair.
PAGE_ONE = [
    (
        72,
        [
            "A Small Paper About Federated Learning Systems",
            "This paper studies the behaviour of feder-",
            "ated learning under a network that drops a",
            "large share of the client updates it carries.",
            "We report one result.",
            "Our method does not yet handle clients that",
            "leave in the middle of a training round, and",
            "that is the obvious next step for this work.",
        ],
    )
]

# Page two prints two columns, so the reader has to finish the left one before it starts
# the right one. Read straight across, the two texts interleave line by line.
PAGE_TWO = [
    (
        60,
        [
            "The left column opens the section and",
            "runs for several lines before it stops.",
            "It closes here.",
        ],
    ),
    (
        330,
        [
            "The right column carries the rest of the",
            "same section and finishes the page off.",
            "It closes here too.",
        ],
    ),
]

# Page three holds the reference list, the way a real paper does: last.
PAGE_THREE = [
    (
        72,
        [
            "References",
            "Smith, J. 2020. Another paper. Journal of Things.",
            "Jones, A. 2019. A third paper. Journal of Things.",
        ],
    )
]

SAMPLE = [PAGE_ONE, PAGE_TWO, PAGE_THREE]


def _content(columns) -> bytes:
    """Build the drawing instructions of one page."""

    text = ""
    for column in columns:
        left_edge, lines = column[0], column[1]
        sideways = len(column) > 2 and column[2] == "sideways"

        if sideways:
            # Tm sets the text matrix. "0 1 -1 0" turns the text a quarter turn, so it
            # reads bottom to top up the left edge of the page.
            text += f"BT /F1 9 Tf 11 TL 0 1 -1 0 {left_edge} 300 Tm\n"
        else:
            text += f"BT /F1 11 Tf 14 TL {left_edge} 700 Td\n"

        for line in lines:
            text += f"({line}) Tj T*\n"
        text += "ET\n"
    return text.encode("latin-1")


def build(pages) -> bytes:
    """Build a whole PDF file from a list of pages."""

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"",  # filled in below, once the page numbers are known
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    # Object 1 is the catalog, 2 is the page list, 3 is the font. Each page then takes
    # two objects: the page itself and the drawing instructions it points at.
    kids = []
    for number, columns in enumerate(pages):
        page_number = 4 + number * 2
        kids.append(b"%d 0 R" % page_number)
        stream = _content(columns)
        objects.append(
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 3 0 R >> >> /Contents %d 0 R >>"
            % (page_number + 1)
        )
        objects.append(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")

    objects[1] = b"<< /Type /Pages /Kids [%s] /Count %d >>" % (
        b" ".join(kids),
        len(pages),
    )

    out = b"%PDF-1.4\n"
    # A PDF ends with a table of byte offsets, one per object, so a reader can jump
    # straight to any object. We record each offset as we write it.
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + body + b"\nendobj\n"

    start_of_table = len(out)
    out += b"xref\n0 %d\n" % (len(objects) + 1)
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += b"%010d 00000 n \n" % offset
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\n" % (len(objects) + 1)
    out += b"startxref\n%d\n%%%%EOF\n" % start_of_table
    return out


# A page carrying the arXiv stamp sideways down its left edge, beside ordinary body
# text. Built on demand by a test rather than saved, because only one test reads it.
STAMPED_PAGE = [
    (
        72,
        [
            "A Small Paper About Federated Learning Systems",
            "The body of the paper starts here and runs on.",
            "We report one result.",
        ],
    ),
    (20, ["arXiv:2005.05265v1  [cs.IT]  11 May 2020"], "sideways"),
]


def build_with_sideways_stamp() -> bytes:
    """One page of body text with the arXiv stamp printed sideways beside it."""

    return build([STAMPED_PAGE])


if __name__ == "__main__":
    path = Path(__file__).with_name("sample_paper.pdf")
    path.write_bytes(build(SAMPLE))
    print(f"Wrote {path} ({path.stat().st_size} bytes)")
