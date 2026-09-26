# Two-stage judging, with the pre-filter measured

Refutation retrieves a deliberately large candidate set, because missing the paper that solved a
problem is the worst output this system can produce. Judging every candidate with a strong model
is the only meaningful cost in the design. So a cheap model first answers whether a candidate
could plausibly address the problem, and only survivors reach the strong model that produces the
Verdict.

This buys cost at the risk of a silent failure: a pre-filter that drops the solving paper produces
a false Untouched, and nothing downstream can detect it. The pre-filter therefore keeps its own
measured number, recall on known solving papers from the hand-labeled set, reported alongside
retrieval recall and per-class Verdict accuracy. If that recall is not near perfect, the
pre-filter is removed and the candidate set shrinks instead.
