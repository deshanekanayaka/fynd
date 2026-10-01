# Fynd

A tool that gives a final year student an approvable starting point for a project: a real
problem from the research literature, an honest account of what has already been done
about it, and a version of it the student can build and evaluate inside the university
deadlines.

## The literature

**Source Paper**:
A published paper inside the Field Scope that states an open problem of its own.
_Avoid_: Reference, citation, article

**Author-Stated Open Problem**:
A specific problem an author says is unsolved, taken from the paper's own Limitations,
Future Work, or Conclusion. It is a claim, not yet an Angle. It is one sentence, and the
sentence before it and the sentence after it travel with it as its context, because a
sentence such as "this remains an open question" carries no meaning alone.
_Avoid_: Future work, limitation, open question

**Field Scope**:
The one field the system covers: computer science papers with open full text and exact
publication dates. Chosen because Refutation needs full text, not abstracts.
_Avoid_: Domain, topic, subject area

**Seeded Domain**:
One of roughly twelve areas inside the Field Scope whose papers are collected in advance.
A student picks a Seeded Domain. The system does not accept a free text field, because an
uncollected area returns nothing.
_Avoid_: Topic, query, search term

**Corroboration**:
The number of separate groups that state the same Author-Stated Open Problem. One author's
future work sentence is often just their next paper. The same problem named by five groups
is a problem the field has. A ranking signal shown in the brief, never a gate, because
gating on it would delete most Alternatives.
_Avoid_: Frequency, popularity, consensus

**Snapshot**:
The set of papers collected for one Seeded Domain, gathered once. Its collection date is
printed on every Research Brief, because an Untouched Verdict is only true as of that date.
One Snapshot holds the papers on both sides of a cutoff date. The cutoff belongs to
Refutation and never to collection, and every paper carries its own publication date, so
the side a paper falls on is read from the paper and never from where it is stored.
_Avoid_: Corpus, index, dataset

**Paper Text**:
The readable prose of one paper, with the reference list dropped. It is what Refutation and
problem extraction read, because an abstract never states a limitation in enough detail.
_Avoid_: Full text, body, content

**Prior Work**:
The specific published work an Angle differs from. Named with a citation. An Angle with no
Prior Work named is discarded.
_Avoid_: Related work, literature, background

**Reported Limitation**:
A passage where somebody states a weakness in Prior Work. It is what makes an Angle's
difference worth trying. The difference is derived from the Reported Limitation, in that
order. Inventing a difference first and then hunting for a limitation to justify it
produces confident nonsense, because some limitation can always be bent to fit.
_Avoid_: Weakness, flaw, criticism

## The task

**Refutation**:
The attempt to find later work that addressed an Author-Stated Open Problem, run against a
cutoff date. Refutation classifies. It does not reject. Its verdict decides which kind of
Angle the problem becomes.
_Avoid_: Validation, verification, filtering

**Candidate Verdict**:
The answer for one Author-Stated Open Problem against one candidate later paper: Filled,
Partly Addressed, or Untouched, with a quoted passage for anything other than Untouched.
It is the unit the judge answers at and the unit a person hand labels. One problem carries
several, one per candidate later paper.
_Avoid_: Judgment, pair, label, finding

**Verdict**:
The result of Refutation: Filled, Partly Addressed, or Untouched. Any verdict other than
Untouched carries a quoted passage from the later paper. It is the aggregate of the
Candidate Verdicts for one problem, and the strongest claim wins: one Filled makes the
Verdict Filled, otherwise one Partly Addressed makes it Partly Addressed, otherwise
Untouched. One paper that solved the problem closes it, whatever the others say. The same
rule means a single wrong Filled destroys a real Gap, so a Candidate Verdict that carries
no quoted passage is rejected and counted, and never reaches the aggregate.
_Avoid_: Score, rating, label

**Angle**:
A problem plus the specific way one project would differ from Prior Work. The unit handed
to a student. Every Angle names its Prior Work, its Reported Limitation, and its Baseline.
_Avoid_: Idea, topic, opportunity

**Gap**:
The kind of Angle where Refutation returned Untouched: nobody has done it. The best kind,
and the one the product leads with. It is not the only kind.
_Avoid_: Research gap, opportunity, unexplored area

**Transfer**:
The kind of Angle where Refutation returned Partly Addressed: somebody did it in one
setting and nobody tried it in another. Its Baseline is their published result.
_Avoid_: Extension, generalisation, port

**Alternative**:
The kind of Angle where Refutation returned Filled: the problem is solved, and the project
solves it a different way. Its Baseline is the existing solution, and its claim is the
difference. This is the safest kind for a student.
_Avoid_: Reimplementation, improvement, variation

**Feasible Slice**:
A proposal for software that acts on an Angle, and that one student can build and evaluate
inside the university deadlines.
_Avoid_: Scope, MVP, subset

**Project Form**:
The kind of software a Feasible Slice is: a web application, a mobile application, a game,
a database system, a robotics build, or a research study. An open set held as a controlled
vocabulary, so Forms stay comparable across runs. A new Form is added deliberately when an
Angle fits none of the existing ones. The system names the Form that fits the Angle. It
does not ask the student to pick.
_Avoid_: Project type, category, deliverable

**Slice Condition**:
One of the six conditions every Feasible Slice must meet, whatever its Project Form. The
output is software. There is one measurable claim. There is a Baseline. The evidence needed
to evaluate it is obtainable without an institutional agreement. There are no human
participants. One student can build it inside the deadlines. A Feasible Slice that fails a
Slice Condition is discarded. This is the only reason anything is discarded.
_Avoid_: Requirement, criteria, rule

**Baseline**:
The existing result a student's result is compared against. Required in every Project Form,
because a project with nothing to compare against produces no result.
_Avoid_: Benchmark, control, reference

**Evaluation Plan**:
The part of a proposal that names the metric, the Baseline, the data source, and how the
number gets computed. Generated per proposal, because Project Form is an open set.
_Avoid_: Methodology, test plan, validation

**Resolution Check**:
The automated attempt to confirm that a data source and a Baseline named in an Evaluation
Plan point at something real. A proposal that fails Resolution Check is discarded. It
exists because a language model writes convincing Evaluation Plans that cannot be run.
_Avoid_: Sanity check, validation, verification

**Setting**:
A real situation where an Angle shows up in practice, attached after the Angle is fixed.
The Setting never changes the Angle. It is illustration, and it is not checkable, so it is
shown separately. A Setting built on United Kingdom open data raises a proposal's rank,
because it gives the student local domain experience. It is a ranking signal, never a
requirement.
_Avoid_: Use case, context, application

**Risk Checkpoint**:
A dated point in the student's timeline where they learn whether the project will work.
Reported with every proposal, next to the reason it is risky.
_Avoid_: Milestone, deadline, gate

**Research Brief**:
The output handed to the student. It carries up to three proposals, one Gap, one Transfer,
and one Alternative, so the whole risk range is on one page. When a Seeded Domain yields
fewer, it returns fewer and states which kind was missing and why. It never pads.
Each proposal has an Angle,
its Refutation evidence, a Feasible Slice with a named Project Form, a Baseline, an
Evaluation Plan, a Risk Checkpoint, predicted supervisor questions with grounded answers,
and a plain explanation of every abstract concept it uses.
_Avoid_: Report, summary, output

## The measurement

**Backtest**:
Running Refutation with a historical cutoff date, then checking each Verdict against what
is known today. It measures whether Refutation classifies correctly. A Backtest is always
reported with the number of Verdicts it covers, because ten Verdicts is a smoke test and
fifty is the floor for a number worth quoting.
_Avoid_: Validation, evaluation, testing

**Leak**:
Information from after the cutoff date reaching a Backtest. Citation counts and
Corroboration counts both carry it, because both grew after the cutoff. A leaked Backtest
reports a number better than the truth.
_Avoid_: Bias, contamination, overfitting

**Grounding Metric**:
A score that measures whether output reflects retrieved text, such as faithfulness or
citation coverage. Named here to keep it separate from correctness. A Research Brief can
score highly on every Grounding Metric while misclassifying every Verdict.
_Avoid_: Accuracy, quality score, confidence

## Decisions recorded as language

**Unstudied Combination**:
An Angle inferred from an empty cell in a matrix of methods against problems or datasets.
Excluded from this version. An empty cell is usually empty because the combination is
pointless, and telling the difference needs a domain expert.

**Replication Gap**:
A finding never replicated, or one that two papers contradict. Excluded from this version.
A good later addition, not a first one.
