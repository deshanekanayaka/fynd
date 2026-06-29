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