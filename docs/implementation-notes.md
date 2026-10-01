
### OBS-004: Unreadable symbols arrive as "(cid:101)"

**Found:** 2026-10-01, while reading the sentences that the problem extractor rejected.

**What arrives.** 179 of the 2787 sentences in the Phase 0 Snapshot, which is 6.4 percent, hold
at least one token of the form `(cid:51)`. The number changes but the shape does not. Examples
from the real papers:

```
SecureBoost (cid:55) (cid:51) (cid:55) (cid:51) [Cheng et al., 2019]
the total privacy expense is limited at (cid:101) = 4
```

**Cause.** A PDF can carry a cut down copy of a font holding only the letters the paper uses.
Each shape in that copy has a number. A table in the PDF maps the numbers back to characters,
and the paper is allowed to leave the table out. When it is missing, pdfplumber has a shape
number and no character, so it prints the number instead. The first example is a comparison
table whose tick and cross marks are codes 51 and 55. The second is the Greek letter epsilon,
code 101, inside a sentence about a privacy budget.

**How widespread.** Very uneven. 106 of 822 sentences in 2007.00914, and 1 of 245 in 2005.05265.
The two commonest codes across the Snapshot are 55 and 51, the tick and the cross, 216 times
together, so most of the damage is in tables rather than in prose.

**Impact today: none.** Phase 0 reads sentences where an author states an open problem, and such
a sentence is prose. No candidate the extractor returned holds one of these tokens.

**Impact later: visible to a student.** A Research Brief quotes a passage. A quoted passage
reading "the total privacy expense is limited at (cid:101) = 4" reads as a broken tool, and the
same sentence given to a judge has lost the symbol the claim turns on.

**Why it is not fixed now.** The cheap repair is to delete the tokens, and it is wrong for prose.
Deleting the ticks from a table loses nothing. Deleting epsilon from a sentence about a privacy
budget leaves a sentence that looks correct and no longer is, which is worse than one that
looks broken. Telling those two cases apart is the actual work, and no Verdict depends on it
yet. The ticket is `.scratch/extractor-glyphs/issues/01-unmapped-glyphs.md`.

**What it confirms about practice 2 in OBS-003.** This was found by reading output, again, and
by reading the part of the output that was thrown away rather than the part that was kept. The
rejected sentences of a filter are a place real findings hide.
