# Fynd: stack and sequencing

`docs/design/big-picture.md` describes what the system does, with no technology names. This
document names the technology and the build order. Terms with capital letters are defined in
`CONTEXT.md`.

## Standing constraint

Free where a free option exists. Where it does not, the cost is named below with its reason.

## The stack

| Role | Choice | Why |
|---|---|---|
| Cloud account | Amazon Web Services | Preferred by the target job descriptions |
| Raw full text | S3 | Cheap object storage, a few cents at this size |
| Operational store | Postgres with pgvector, Supabase free tier | One store for statements, groups, Verdicts, and the vector index. Free. Already known from Diacify |
| Batch compute | Fargate tasks, triggered by EventBridge Scheduler | Pay per run, nothing always on |
| Refutation loop | LangGraph | The loop has an explicit state object: candidate problem, retrieved papers, per-paper judgments, aggregated Verdict, cutoff date |
| Run tracking | MLflow, self-hosted locally | Records each Backtest with its configuration and per-class precision and recall |
| Call tracing | LangSmith | Records individual judge calls, so a wrong Verdict can be read back |
| Orchestration | Airflow in Docker, locally | Runs Backtest backfills across cutoff dates |
| Continuous integration | GitHub Actions | Free on public repositories |
| Cloud resources | Terraform | One environment |
| Interface | Read-only site listing prepared Seeded Domains and their briefs | No accounts. Diacify already proves full-stack work |

Local development runs in containers. It is not described in Terraform.

## Deviations, recorded on purpose

1. No dedicated vector database. pgvector in the same Postgres removes the second store the
   first version had, and the consistency problem that came with it.
2. No Glue, Athena, or Iceberg. Postgres is sufficient at this data size. A columnar query
   engine on top of a dataset that fits in memory is a weaker answer than saying it was not
   needed.
3. Airflow runs locally, not in the cloud. Managed orchestration costs several hundred
   dollars a month, and a small always-on instance would be the only server in the design
   needing patching. Backfill happens while developing, not in production.
4. One environment, not two. A second environment doubles cost and teaches nothing extra at
   this scale.

## Where the money actually goes

Everything above is free or costs a few cents a month, with one exception: the model calls
that produce Verdicts. A Backtest judges many candidate later papers per problem, and the
strong model reads real passages, so token cost is the only figure that can grow without
being noticed.

Four controls hold it down:

1. A two-stage judge. A cheap or free model answers "could this paper plausibly address this
   problem", and only survivors reach the strong model that produces the Verdict. The
   pre-filter's recall on known solving papers is measured against hand labels and reported,
   because a pre-filter that drops the solving paper produces a false Untouched invisibly.
2. Judge passages, never whole papers.
3. Cache every judgment by problem and paper pair, so a rerun with a changed prompt
   elsewhere does not re-pay for unchanged work.
4. Set a hard monthly spend cap and treat hitting it as a bug, not an inconvenience.

## Build order

The single number that can kill this project is per-class accuracy on the Verdict,
especially Partly Addressed. It comes first, before any application, cloud, or
orchestration exists.

**Phase 0, smoke test, local only.** Seeded Domain: federated learning. Cutoff: 2022.
Collect a small Snapshot, extract Author-Stated Open Problems, hand-label ten Verdicts, run
the judge, compare. Plain Python, no framework. Then a written go or no-go.

Reuse from the first version: `backend/src/ingest/fetch_papers.py`,
`pdf_extractor.py`, and `chunker.py`, with their tests. Extraction must work at the sentence
level rather than by heading, because OBS-001 in `docs/v1-implementation-notes.md` shows that
explicit Limitations and Future Work headings are almost absent from arXiv papers.

Replaced in later phases: `embedder.py` and `vector_store.py` target Chroma, and the current
design uses Postgres with pgvector instead. They stay in the repository until Phase 1 needs
the change.

**Phase 1, the Refutation engine.** Retrieval tuned and measured for recall of the solving
paper, separately from judge accuracy. The two-stage judge, with the pre-filter's recall
measured separately again. Three-valued Verdict, with a quoted passage required
for anything other than Untouched. Per-class precision and recall, recorded in
MLflow. The Leak guard: every count recomputed as of the cutoff.

Hand labeling volume. Fifty labels is the floor, weighted toward Partly Addressed because it
is the class most likely to fail, and the wider uncertainty is stated in the README. One
hundred and fifty is the target. In practice, fifty labels means about twelve problems with
four or five candidate later papers each, so about sixty papers touched and three to four
hours. One hundred and fifty means about thirty problems and about one hundred and fifty
papers touched, so eight to twelve hours. Only passages are read, never whole papers. The
Snapshot is separate and much larger, a few thousand papers collected by machine and never
read by hand.

**Phase 2, grouping.** Candidate neighbours fetched by vector similarity, then same-or-
different judged per pair. Two hundred hand-labeled pairs, precision and recall reported.
Corroboration counts become a ranking signal.

**Phase 3, Angle and Feasible Slice.** The difference is derived from a Reported Limitation,
in that order. The six Slice Conditions applied. Resolution Check discards proposals whose
data source or Baseline does not resolve. Guardrail: reject any Verdict that is not
Untouched and carries no quoted passage, and count the rejections.

**Phase 4, the graph.** Port the stable loop to LangGraph with an explicit state object. Add
LangSmith tracing.

**Phase 5, the pipeline.** Every stage becomes an independent command reading and writing
storage. An Airflow directed acyclic graph runs them locally, including backfill across
several cutoff dates.

**Phase 6, the cloud.** Terraform for S3, the Fargate task definitions, the EventBridge
schedule, and the permissions between them, with secrets referenced rather than stored.
GitHub Actions runs tests and type checks on every push, plus one end-to-end run on a small
fixed fixture with recorded model responses. The real labeled evaluation runs on demand, and
its numbers are recorded, not used as a pass or fail light.

**Phase 7, the interface and the write-up.** The read-only site. The README carries the
per-class Backtest numbers, the retrieval recall number, the model comparison, and one
section saying what the first version of Fynd got wrong.

## Deferred until the Backtest numbers are good

Accounts, generation on request, monetization, and abuse controls are all out of scope until
per-class Verdict accuracy is known. They are one decision, not four: generation on request is
the only action that spends money per click, so it creates both the revenue and the abuse at
the same time. Until it exists, a read-only site of prepared briefs has nothing behind a
signup to consume, so signup fraud cannot cost anything.

If it is revisited, the free controls come first: email verification, rate limits per address
and per account, a hard cap on requests, and a spend cap at the model provider. A paid
verification service is considered only after those four prove insufficient.

Monetization is a hard business and a separate project. Students buy once per lifetime, the
buying window is a few weeks once a year, and the competitor is a free chatbot that answers
worse but instantly. The Backtest numbers are the only honest reason a student would choose
this instead.

## The fallback, decided now

If Partly Addressed cannot be judged reliably after Phase 1, drop the Transfer kind and ship
two kinds instead of three. The Research Brief then carries one Gap and one Alternative. It
is a smaller product and an honest one. Deciding this now keeps the decision calm when it
arrives.
