"""Step 02 of ingestion: turn one paper PDF into Paper Text.

An author states the limits of their own work in the Limitations, the Future Work, or
the Conclusion. None of those sit in the abstract, so Fynd has to read the body, and the
body only arrives as a PDF. Step 03 then splits this text into sentences, so the text
has to read like prose and not like a column of broken lines. The repair work lives
here, before 03 ever sees it.
"""

import io
import re
import statistics
import unicodedata

import pdfplumber
import requests

TIMEOUT_SECONDS = 30

# A normal arXiv paper is under 30 pages. Anything far past that is a thesis or a survey
# with a long appendix, and reading it costs time for text Fynd does not need.
MAX_PAGES = 60

# A line shorter than this share of the median line ends a paragraph. On a two column
# page the median is taken per column, because _paragraphs runs on one column at a time.
SHORT_LINE_RATIO = 0.7

# A page is two column when under this share of its words cross the middle of the page.
# Measured on real papers: a two column page has about 1 word in 361 crossing, and a one
# column page has about 1 in 5, so anything between these two numbers works.
GUTTER_RATIO = 0.05

# ...and when each half holds at least this share of the words. Without the second test,
# a page of short lines that all sit in the left half looks like a two column page whose
# right column is empty, and the split then cuts the ends off those lines.
HALF_RATIO = 0.2

# How far apart two letters can sit before pdfplumber puts a space between them. The
# default of 3 is too wide for a tightly set justified column, where it returns
# "imagemodelscanautomatically" as one word.
X_TOLERANCE = 1.5

# Typesetting characters that carry no meaning for us. A judge prompt and a sentence
# splitter both read plain quotes more reliably than curly ones.
REPLACEMENTS = {
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u2013": "-",
    "\u2014": "-",
}

# A heading that starts the reference list, alone on its line. Allows a leading section
# number, such as "5. References", and any capitalization.
REFERENCES_HEADING = re.compile(
    r"^\s*(?:\d+\.?\s*)?(?:references|bibliography)\s*$",
    re.IGNORECASE,
)

# arXiv asks tools to name themselves, so a misbehaving script can be contacted rather
# than silently blocked.
HEADERS = {"User-Agent": "fynd/0.1"}

# A paper PDF is a few megabytes, and a long survey with figures reaches about twenty.
# Eighty is far past any real paper, so this stops a redirect or a broken mirror from
# filling memory with a reply we never asked for.
MAX_BYTES = 80 * 1024 * 1024

# How many bytes to take from the connection at a time.
CHUNK_BYTES = 64 * 1024


def _download(pdf_url: str) -> bytes:
    """Fetch the bytes of one PDF. Raises ValueError when they are not a PDF."""

    # stream=True holds the body back, so the size test runs while the bytes arrive
    # instead of after all of them already sit in memory. The `with` closes the
    # connection on the way out, including when a check inside it raises.
    with requests.get(
        pdf_url, timeout=TIMEOUT_SECONDS, headers=HEADERS, stream=True
    ) as response:
        # Raise rather than return None. A caller can ignore None by accident, and a
        # paper that silently became empty text is a false Untouched Verdict later on.
        if response.status_code != 200:
            raise ValueError(f"{pdf_url} returned status {response.status_code}")

        # Count the bytes we actually read. A Content-Length header is a claim by the
        # server, and a limit that trusted the claim would let a server that sends more
        # than it promised walk straight past the limit.
        data = bytearray()
        for chunk in response.iter_content(CHUNK_BYTES):
            data.extend(chunk)
            if len(data) > MAX_BYTES:
                raise ValueError(f"{pdf_url} is larger than {MAX_BYTES} bytes")

    # Trust the bytes, not the Content-Type header. An arXiv error page or a rate limit
    # page can still be served with a PDF content type.
    if not data.startswith(b"%PDF"):
        raise ValueError(f"{pdf_url} did not return a PDF")

    return bytes(data)


def _paragraphs(page_text: str) -> str:
    """Join the printed lines of one page back into paragraphs."""

    lines = [line.strip() for line in page_text.split("\n") if line.strip()]
    if not lines:
        return ""

    # A paper prints justified columns, so every full line is nearly the same width and
    # the last line of a paragraph is the short one. That short line is the only signal
    # we get: pdfplumber almost never emits a blank line inside a column.
    short_line_length = statistics.median(len(line) for line in lines) * SHORT_LINE_RATIO

    paragraphs = []
    current = ""
    for line in lines:
        # A heading stands alone. Without this, "References" joins the end of the
        # paragraph above it whenever that paragraph did not close on a short line,
        # and _cut_references then finds no heading to cut at.
        if REFERENCES_HEADING.match(line):
            if current:
                paragraphs.append(current)
            paragraphs.append(line.strip())
            current = ""
            continue

        if current == "":
            current = line
        elif current.endswith("-"):
            # "feder-" then "ated" is one word the line break cut in half, so the hyphen
            # goes. A capital or a digit after it means a real hyphen, such as
            # "Transformer-XL", so the hyphen stays. Either way no space is added: the
            # two halves are one word.
            if line[0].islower():
                current = current[:-1] + line
            else:
                current = current + line
        else:
            current = current + " " + line

        if len(line) < short_line_length:
            paragraphs.append(current)
            current = ""

    if current:
        paragraphs.append(current)

    return "\n\n".join(paragraphs)


def _strip_between(page, left_edge: float, right_edge: float) -> str:
    """Read the text between two upright edges of one page."""

    strip = page.crop((left_edge, 0, right_edge, page.height))
    # extract_text returns None for a strip that holds only a figure.
    return strip.extract_text(x_tolerance=X_TOLERANCE) or ""


def _is_two_column(page) -> bool:
    """Say whether this page prints two columns."""

    words = page.extract_words()
    if not words:
        return False

    middle = page.width / 2

    # A word that starts left of the middle and ends right of it crosses the gutter.
    # On a two column page almost nothing does, because the gutter is empty space.
    crossing = [word for word in words if word["x0"] < middle < word["x1"]]
    if len(crossing) / len(words) >= GUTTER_RATIO:
        return False

    # Both halves must hold real text. A page of short lines that all sit in the left
    # half crosses nothing either, and slicing that page cuts the ends off its lines.
    share_on_the_right = len([w for w in words if w["x0"] >= middle]) / len(words)
    return HALF_RATIO < share_on_the_right < 1 - HALF_RATIO


def _upright_only(page):
    """Drop the characters printed sideways.

    arXiv stamps "arXiv:2005.05265v1 [cs.IT] 11 May 2020" down the left edge of page 1,
    rotated a quarter turn. Read with the rest of the page it arrives reversed, as
    "0202 yaM 11", and worse, it shares rows with the body, so pdfplumber puts "0202" in
    front of a real sentence. A paper prints nothing else sideways.
    """

    return page.filter(lambda obj: obj.get("upright", True))


def _page_text(page) -> str:
    """Read one page, splitting it into two columns when it has two."""

    page = _upright_only(page)

    if not _is_two_column(page):
        return _paragraphs(_strip_between(page, 0, page.width))

    # Read the halves one after the other. Without this, pdfplumber reads straight
    # across both columns, and the two column texts interleave line by line.
    # ponytail: a full width title or table on a two column page gets sliced down the
    # middle. The title already lives in the Paper Record from step 01, so the cost is
    # a few broken lines. Detect spanning lines per line if it ever matters.
    middle = page.width / 2
    left = _paragraphs(_strip_between(page, 0, middle))
    right = _paragraphs(_strip_between(page, middle, page.width))
    return left + "\n\n" + right


def _read_pages(data: bytes) -> str:
    """Turn the bytes of a PDF into text, one paragraph per line block."""

    with pdfplumber.open(io.BytesIO(data)) as pdf:
        pages = pdf.pages
        if len(pages) > MAX_PAGES:
            print(f"Paper has {len(pages)} pages. Reading the first {MAX_PAGES}.")
            pages = pages[:MAX_PAGES]

        return "\n\n".join(_page_text(page) for page in pages)


def _normalize(text: str) -> str:
    """Replace typesetting characters with plain ones."""

    # NFKC turns the ligature characters into the letters they stand for, so the single
    # character "fi" becomes "f" and "i". It keeps accented letters whole, because an
    # author name with an accent is not a bug.
    text = unicodedata.normalize("NFKC", text)
    for odd, plain in REPLACEMENTS.items():
        text = text.replace(odd, plain)
    return text


def _cut_references(text: str) -> str:
    """Drop the reference list at the end of the paper."""

    lines = text.split("\n")

    # Search from the end. The words "References" and "Bibliography" appear in the body
    # of a paper too, and the real heading is the last one.
    for index in range(len(lines) - 1, -1, -1):
        if REFERENCES_HEADING.match(lines[index]):
            kept = "\n".join(lines[:index])
            dropped = len("\n".join(lines[index + 1 :]))
            print(f"Cut {dropped} characters of references")
            return kept

    # No heading found. Keep everything rather than guess, and say so, because a paper
    # whose references stay in produces junk sentences in step 03.
    print("No references heading found. Keeping the whole text.")
    return text


def extract_paper_text(pdf_url: str) -> str:
    """Download one paper PDF and return its Paper Text."""

    data = _download(pdf_url)
    raw_text = _read_pages(data)
    plain_text = _normalize(raw_text)
    paper_text = _cut_references(plain_text)

    # A scanned paper holds pictures of words, so every page returns nothing. Empty text
    # read as a paper is a false Untouched Verdict later on, so it has to raise here.
    if not paper_text.strip():
        raise ValueError(f"{pdf_url} produced no text. It is probably a scanned paper.")

    return paper_text


if __name__ == "__main__":
    # The paper that named federated learning. It is inside the Phase 0 Seeded Domain
    # and well before the 2022 cutoff.
    text = extract_paper_text("https://arxiv.org/pdf/1602.05629v1")
    print(f"Paper Text is {len(text)} characters")
    print("--- the last 800 characters ---")
    print(text[-800:])
