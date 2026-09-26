# Fynd: the big picture

No technology names appear in this document. Every component is described by what it does
and why it exists. Terms with capital letters are defined in `CONTEXT.md`.

## What the system is for

A final year student has two to three weeks to get a project idea approved, then three
deadlines to build and evaluate it. Most students start by asking "what application can I
build", and supervisors reject the result for having no research foundation. Fynd starts
from the other end. It reads what researchers themselves say is unsolved, finds out what
has actually been done about it since, and hands the student a project that already has a
justification and something to measure against.

## What the student receives

One Research Brief. It carries up to three proposals: one Gap, one Transfer, and one
Alternative. The three kinds sit on one page on purpose, because the real decision the
student makes is how much to gamble, not which topic sounds nicer.

Each proposal contains:

1. The Angle: the problem, and the specific way this project differs from Prior Work.
2. The Refutation evidence: what later work exists, with a quoted passage.
3. The Feasible Slice: what to build, with a named Project Form.
4. The Baseline and the Evaluation Plan: what the result is compared against, and how the
   number gets computed.
5. The Risk Checkpoint: the date the student learns whether the project will work.
6. Predicted supervisor questions, with answers grounded in the cited papers.
7. A plain explanation of every abstract concept the proposal uses.
8. The Snapshot collection date, because an Untouched Verdict is only true as of that date.

## The pipeline

```
Student picks a Seeded Domain
             │
             ▼
 ┌─────────────────────────────┐
 │ 1. Collect the Snapshot     │  papers, full text, exact dates, citation links
 └─────────────────────────────┘
             │
             ▼
 ┌─────────────────────────────┐
 │ 2. Extract stated problems  │  from Limitations, Future Work, Conclusion
 └─────────────────────────────┘
             │
             ▼
 ┌─────────────────────────────┐
 │ 3. Group equal problems     │  → Corroboration count per group
 └─────────────────────────────┘
             │
             ▼
 ┌─────────────────────────────┐
 │ 4. Refute against a cutoff  │  → Verdict: Filled | Partly Addressed | Untouched
 └─────────────────────────────┘
             │
             ▼
 ┌─────────────────────────────┐
 │ 5. Form the Angle           │  Verdict decides the kind
 └─────────────────────────────┘     Untouched → Gap
             │                       Partly Addressed → Transfer
             │                       Filled → Alternative
             ▼
 ┌─────────────────────────────┐
 │ 6. Shape the Feasible Slice │  Project Form, Evaluation Plan, six Slice Conditions
 └─────────────────────────────┘
             │
             ▼
 ┌─────────────────────────────┐
 │ 7. Resolution Check         │  data source and Baseline must resolve, or discard
 └─────────────────────────────┘
             │
             ▼
 ┌─────────────────────────────┐
 │ 8. Rank and select          │  best of each kind; Corroboration and a United
 └─────────────────────────────┘  Kingdom Setting raise rank
             │
             ▼
 ┌─────────────────────────────┐
 │ 9. Assemble the brief       │  Setting, Risk Checkpoint, supervisor questions,
 └─────────────────────────────┘  concept explanations, collection date
             │
             ▼
      Research Brief
```

## Why each stage exists

1. Collect the Snapshot. Refutation can only find later work that is present. Coverage
   decides whether a Verdict is trustworthy, so the Snapshot is the foundation and its date
   is part of the output.
2. Extract stated problems. Headings cannot be trusted for this. The first version of Fynd
   ingested forty papers and found zero chunks under an explicit Limitations or Future Work
   heading, while one hundred and forty-nine chunks carried that language inline, inside
   introductions, bodies, and conclusions. Authors state what they did not do wherever they
   like. So extraction works at the sentence level, on language such as "we did not address",
   "a limitation of", and "future work could", and a heading is a ranking signal rather than
   a filter. See OBS-001 in `docs/v1-implementation-notes.md`. An extracted statement is a
   claim about a problem, not yet an Angle.
3. Group equal problems. "Performance under label skew is unaddressed" and "we did not
   evaluate on non-identically distributed clients" are one problem in two wordings.
   Grouping them produces the Corroboration count, which tells the student whether the
   field has this problem or one author had it.
4. Refute against a cutoff. Later work is found two ways: papers that cite the Source
   Paper, and papers that match the problem statement directly. The second way matters,
   because the group that solved a problem often never cited the paper that stated it.
5. Form the Angle. The Verdict decides the kind. For a Transfer or an Alternative, the
   difference is derived from a Reported Limitation, in that order. Inventing a difference
   first and hunting for a justification afterwards produces confident nonsense.
6. Shape the Feasible Slice. The Project Form is chosen to fit the Angle, not the student's
   preference, because some problems have nothing to build and wrapping them in an
   application is the decoration supervisors reject.
7. Resolution Check. A language model writes convincing Evaluation Plans that cannot be
   run. It names datasets that do not exist and baselines nobody published. A clueless
   student will not catch that, and the failure surfaces in week five.
8. Rank and select. A single combined score returns three Alternatives every time, because
   they are the easiest to justify, and then the student never learns the ambitious option
   existed.
9. Assemble the brief. The Setting makes the problem legible. The supervisor questions turn
   an artifact the student carries into an argument the student owns.

## What gets measured

The headline number is the Backtest. Run Refutation with a historical cutoff, then check
each Verdict against what is known today, and report precision and recall for each of the
three Verdict classes separately. Partly Addressed will be the worst class, and a single
accuracy figure hides that.

The Backtest has one failure mode that matters more than any other: the Leak. Citation
counts and Corroboration counts both grew after the cutoff, so both must be recomputed as
of the cutoff date. A leaked Backtest reports a number better than the truth, and the
number is believable, which is what makes it dangerous.

Three smaller measurements support it:

1. Problem grouping: precision and recall of the same-or-different pair judgment, against
   hand labels.
2. Limitation match: whether a difference genuinely answers the Reported Limitation it
   cites, spot-checked against hand labels.
3. Resolution Check pass rate: the share of proposals whose named data source and Baseline
   resolve.

Grounding Metrics such as faithfulness and citation coverage stay as guardrails. They are
not the headline, because output can reflect the retrieved text perfectly and still
misclassify every Verdict.

Every reported number comes from hand labels, because no public dataset records whether a
stated open problem was later addressed. A smoke test of ten labels decides whether to keep
going. Roughly one hundred and fifty labels is the price of putting a figure in the README.

## What is deliberately excluded

1. Unstudied Combination and Replication Gap as sources of Angles. Later versions.
2. Free text domains. A student picks a Seeded Domain, because an uncollected area returns
   nothing and nothing is what the product exists to replace.
3. Blockchain components in proposed Feasible Slices, in every Project Form, because a
   blockchain component almost never carries a measurable claim.
4. Projects whose evidence depends on recruiting human participants. Ethics approval eats
   the timeline.
5. A requirement that the Setting use United Kingdom open data. It raises rank instead,
   because a game or a robotics build has no United Kingdom dataset in it.
6. Scheduled Snapshot refresh. Worth building later. It does not decide whether the first
   version is true.
7. Accounts, generation on request, monetization, and abuse controls. Deferred until the
   Backtest numbers are known. See `stack-and-sequencing.md`.

## The two rules that keep it honest

Nothing is accepted until an automated attempt to falsify it fails. Refutation applies that
to the problem. Resolution Check applies it to the Evaluation Plan.

Nothing is discarded for lack of novelty. The only reasons to discard are a failed Slice
Condition and a failed Resolution Check. A solved problem approached a different way is a
legitimate project, and often the safest one.
