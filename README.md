# Fynd

Fynd gives a final year student an approvable starting point for a project: a real problem
from the research literature, an honest account of what has already been done about it, and a
version of it the student can build and evaluate inside the university deadlines.

Status: redesigned, and being rebuilt. The paper collection, PDF extraction, and chunking code
works. Nothing measures correctness yet. No accuracy number appears in this README until hand
labels exist to produce one.

## The idea

A student picks a domain. Fynd reads what researchers themselves say is unsolved, finds out
what later work actually did about it, and returns up to three proposals:

1. A Gap. Nobody has done this. The Baseline is the closest published method.
2. A Transfer. Somebody did it in one setting and nobody tried it in another. The Baseline is
   their published result.
3. An Alternative. The problem is solved, and the project solves it a different way. The
   Baseline is the existing solution, and the claim is the difference.

All three kinds appear on one page, because the real decision a student makes is how much to
gamble.

Each proposal carries the evidence, a named kind of software to build, a Baseline, an
evaluation plan, a dated point where the student learns whether the project will work,
predicted supervisor questions with grounded answers, and a plain explanation of every
abstract concept it uses.

## The technical core

Two components decide whether this works, and both try to falsify a claim before accepting it.

Refutation takes one stated open problem and a cutoff date, searches for later work that
addressed it, and returns Filled, Partly Addressed, or Untouched. Any verdict other than
Untouched carries a quoted passage. The cutoff date is a parameter, so the same engine serves
a student asking today and a historical test.

Resolution Check takes a generated evaluation plan and confirms that the data source and the
Baseline it names point at something real. A language model writes convincing evaluation plans
that cannot be run, and a student will not catch that until week five.

## How it gets measured

The headline number is a backtest. Run Refutation with a 2022 cutoff, then compare each verdict
against what is known today, and report precision and recall for each of the three verdict
classes separately. Partly Addressed is the class most likely to fail, and a single accuracy
figure hides that.

Three supporting numbers exist for a reason. Retrieval recall of the solving paper separates a
retriever that missed the paper from a judge that misread it. Pre-filter recall guards the
cheap first-stage model, because dropping the solving paper produces a false Untouched that
nothing downstream can detect. Problem grouping precision and recall guard the count of how
many groups named the same problem.

Every one of those numbers comes from hand labels, because no public dataset records whether a
stated open problem was later addressed.

## What the first version got wrong

The first version of Fynd is on the `v1-archive` branch. Three mistakes are worth naming.

It treated an author's Future Work sentence as a research gap. It is a claim about a gap. Many
such claims were answered within a year by somebody else, and the first version had no way to
find out.

It measured grounding instead of correctness. Faithfulness, answer relevance, and citation
coverage all ask whether the output reflects the retrieved text. A brief can score highly on
all three and still report a problem that was solved in 2023.

It promised any domain the student typed. Checking whether a problem was later solved needs
open full text and a dense citation graph, and an uncollected domain returns nothing, which is
what the product exists to replace.

## Documentation

1. `CONTEXT.md` defines the language. Every capitalised term in the design comes from there.
2. `docs/design/big-picture.md` describes the system with no technology names.
3. `docs/design/stack-and-sequencing.md` names the stack, the build phases, and the fallback.
4. `docs/adr/` holds the design decisions a future reader will question.
5. `docs/v1-implementation-notes.md` holds implementation findings from the first version.
