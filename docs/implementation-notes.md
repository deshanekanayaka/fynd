# Implementation notes from the current version

Findings from the code on `main` today. Notes from the first version are in
`docs/v1-implementation-notes.md`, and the numbering carries on from that file, so an
OBS number means one thing across the whole repository. Design decisions live in
`docs/adr/`.

## Observations

### OBS-003: A sideways arXiv stamp put its characters inside real sentences

**Found:** 2026-10-01, in the first real run of the ingestion pipeline, on five federated
learning papers collected for Phase 0.

**What the reader sees on the page.** arXiv prints an identifier down the left edge of
page 1 of every paper it hosts, turned a quarter turn, so a human reads it by tilting
their head. On 2005.05265 it says `arXiv:2005.05265v1 [cs.IT] 11 May 2020`. It is 40
characters, and it is not part of the paper. The author never wrote it.

**What arrived instead.** Two separate faults, and the second one is the serious one.

1. The stamp arrived as its own text, read in the wrong direction, so the sentence list
   held `]TI.sc[ 1v56250.5002:viXra` and `0202 yaM 11`. Junk, but obvious junk.
2. The stamp sits beside the body, at the same heights as the body lines. pdfplumber
   groups characters into lines by how high up the page they sit, so it read a piece of
   the stamp and a line of the paragraph as one line. A real body line of 2005.05265
   came out as `0202 between the central server and the distributed local clients`. The
   `0202` is the year 2020 printed sideways and read backwards.

**Why that is worse than junk.** Fault 1 adds sentences nobody asked for, and a later
step can drop them. Fault 2 damages a sentence that Refutation reads and that a Research
Brief quotes back to a student. A quoted passage with `0202` glued to the front of it
reads as a broken tool. If the damaged line had been a Limitations sentence, the
Author-Stated Open Problem taken from it would have been wrong in the student's hands.

**Cause.** `_page_text` read every character on the page. A PDF records a rotation for
each character, and pdfplumber reports it as `upright`. The old code never looked at it.
The 40 sideways characters were treated as ordinary prose.

**How it was found.** Not by a test. The offline test reads a small PDF written by
`tests/fixtures/make_sample_pdf.py`, and that file printed nothing sideways, because the
person who wrote it did not know the stamp existed. It was found by printing the first
two sentences of each of the five papers after the first real run.

**Fix.** `_upright_only` drops every character whose `upright` is false, before the page
is read:

```python
return page.filter(lambda obj: obj.get("upright", True))
```

A paper prints nothing else sideways, so nothing real is lost. The fixture builder can
now print a column rotated, and `test_drops_a_sideways_stamp_without_touching_the_body`
holds the case down. After the fix, the five papers hold no stamp text, and the body line
above reads `in the areas of wireless communications and machine learning`.

**How to stop the next one of these.** The bug class is text that sits on the page and is
not prose: a stamp, a page number, a running header, a watermark, the inside of a figure.
Four practices, in the order they pay off.

1. Read real output by eye after every change to step 02 or step 03. A test built from a
   fixture can only hold what somebody already thought of, and this stamp was invisible
   to a fixture written by somebody who had not seen it. The ticket for a step that reads
   a real world file format must keep a real run in its Done list.
2. Read the first and the last few sentences of each paper, not the counts. Page
   furniture lands at the edges of a page, so it lands at the edges of the sentence list.
   The count moved from 247 to 245 when the stamp went, which no reader would notice.
3. Turn every real finding into a fixture case the same day. The fixture is the record of
   what the real world has already done to us.
4. Ask what the geometry says before reaching for a pattern. The fix is one line because
   the PDF already marks the stamp as turned. A rule that matched the text `arXiv:` would
   have left the reversed copy and the glued line untouched.

**Still open.** The other half of page 1 is not fixed. A line that spans the full width of
a two column page, such as the title, is still cut at the middle, so 2005.05265 gives
`Federated Learning and W`. That is noise and not lost input, because the true title sits
in the Paper Record from step 01 and the body prose is unaffected. The measurement, and
the reason a simple width test is not enough, are in
`.scratch/extractor-page-one/issues/01-full-width-lines.md`.
