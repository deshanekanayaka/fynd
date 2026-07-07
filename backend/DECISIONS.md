# Architecture Decision Records

## ADR-001: PDF word extraction tolerance

**Problem:** pdfplumber's default `x_tolerance=3` failed to detect spaces between
words in LaTeX-generated ArXiv PDFs. Words like "Large Language Models" were
extracted as "LargeLanguageModels" because character gaps were smaller than 3px.

**Options considered:**
- Regex post-processing to re-insert spaces at lowercase→uppercase boundaries
- `extract_words()` with fixed tolerance — same problem, gaps still too small
- `x_tolerance_ratio` — dynamic tolerance as a fraction of font size

**Decision:** `x_tolerance_ratio=0.15` — 15% of font size as the space threshold.

**Why:** Scales with font size across different papers and sections. Fixed pixel
tolerances are too rigid for PDFs with varying typography.

## ADR-002: Manual embedding instead of Chroma's built-in embedding function

**Problem:** Chroma can handle embedding internally if you pass documents without
vectors. But this hides which model is being used and creates a hidden coupling
between ingestion and search.

**Options considered:**
- Let Chroma embed automatically using its default model
- Pass `embedding_function=None` and supply our own vectors explicitly

**Decision:** Supply vectors manually using `all-MiniLM-L6-v2` via
`sentence-transformers`, with `embedding_function=None` in Chroma.

**Why:** The same model must embed chunks at ingestion time and queries at search
time. Making that explicit in code means the model is a visible, swappable config
value rather than a hidden Chroma default. Switching embedding models later is a
one-line change in `config.py`.

## ADR-003: BM25 reads data/chunks/*.json, not Chroma

**Problem:** BM25 retrieval needs access to the same chunk corpus as vector search.
Chroma already stores every chunk, so it's tempting to read chunk text and metadata
back out of Chroma for BM25 too.

**Options considered:**
- Read chunk text and metadata out of Chroma for BM25 as well
- Read `data/chunks/*.json` directly for BM25, independent of Chroma

**Decision:** BM25 reads `data/chunks/*.json` directly.

**Why:** Chroma is the vector store's storage, not a shared chunk database. Reading
JSON keeps each retrieval method independent and testable in isolation. Chunk-count
and metadata parity (5,887 chunks both sides) was verified by diagnostic before
locking this in.

## Observations

### OBS-001: Limitations sections absent in current corpus

**Finding:** After ingesting 40 papers across federated learning and RAG domains,
zero chunks were labelled `limitations` or `future_work` by the chunker. However,
149 chunks contain the words "limitation" or "future work" inline — labelled as
`introduction`, `body`, or `conclusions`.

**Cause:** ArXiv papers rarely use a standalone "Limitations" heading. Authors
embed limitation discussions within other sections, particularly conclusions and
introductions. The chunker's regex only detects explicit headings.

**Impact:** The 1.5x section boost in Milestone 6 will have no effect until this
is addressed. Metadata filtering on `section='limitations'` returns zero results.

**Future fix:** Extend the chunker with a sentence-level classifier that detects
limitation language ("we did not address", "a limitation of", "future work could")
and promotes those chunks to `section_priority=1` regardless of their heading label.
This is a Milestone 2 improvement deferred to a later iteration.

### OBS-002: Metadata key inconsistency between chunker and vector store

**Finding:** Chunks on disk stored `section_priority` as the key. The embedder
renamed it to `priority` when writing metadata to Chroma. Query code looked for
`section_priority` and returned `unknown` for every result.

**Fix:** Standardised to `section_priority` in `vector_store.py`. Removed the
duplicate `arxiv_id` field from Chroma metadata. Re-embedded all chunks.

**Fix:** Added `references` to the heading detection regex in `chunker.py` and
skip references sections in `chunk_paper`. Partially addresses reference noise
in results — papers without an explicit References heading are not yet handled.