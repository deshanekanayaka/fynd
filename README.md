# Fynd

Identify genuine research gaps in academic literature — not summaries, not vague
"further research needed", but specific, cited, actionable gaps for your final year project.

🔗 **[Live demo](https://fynd.vercel.app)** 

---

## What it does

Fynd pulls papers from ArXiv and Semantic Scholar, processes them through a
multi-stage RAG pipeline, and produces a structured research brief answering:
**"What hasn't been studied yet — and where should I focus?"**

Every gap is tied to a real paper, a real section, and a verifiable claim.
No hallucinated summaries.

---
## Architecture

```
Student query (research domain)
           │
           ▼
  Next.js Frontend
           │  POST /api/gaps
           ▼
  FastAPI Backend
           │
           ▼
  [Ingest] ArXiv + Semantic Scholar
           │
           ▼
  [Chunk] Section-aware splitting
  Limitations → Future Work → Conclusion → Abstract → Body
           │
           ▼
  [Embed] all-MiniLM-L6-v2 → ChromaDB
           │
      ┌────┴────┐
      ▼         ▼
   BM25       Vector
   search     search
      │         │
      └────┬────┘
           ▼
  [Fuse] Reciprocal Rank Fusion
           │
           ▼
  [Rerank] ms-marco-MiniLM (1.5× boost for Limitations/Future Work)
           │
           ▼
  [Generate] Gemini 1.5 Flash → cited gaps as structured JSON
```

---

## Tech stack

| Layer | Tool | Why |
|---|---|---|
| Backend | FastAPI | Async, typed, auto-docs. Already production-proven on prior projects |
| Frontend | Next.js 14 + TypeScript | SSR for shareable research brief pages, one-command Vercel deploy |
| Embeddings | all-MiniLM-L6-v2 | Open-source, runs locally, no API cost, 384-dim sweet spot for speed vs accuracy |
| Vector store | ChromaDB → Pinecone | Chroma for dev (zero setup), Pinecone for prod (managed, scalable, same interface) |
| Retrieval | BM25 + Vector + RRF | Hybrid covers both keyword misses (vector) and synonym misses (BM25) |
| Reranking | ms-marco-MiniLM | Cross-encoder accuracy on top-20 candidates without full-corpus latency |
| Generation | Gemini 1.5 Flash | Free tier, structured JSON output, sufficient for cited gap extraction |
| Evaluation | RAGAs | Industry-standard faithfulness, relevance, and citation coverage metrics |

---

## Setup

```bash
# Clone and navigate to backend
git clone https://github.com/deshanekanayaka/fynd.git
cd fynd/backend

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Add your SEMANTIC_SCHOLAR_API_KEY and GEMINI_API_KEY to .env

# Run the ingestion pipeline
python src/ingest/pipeline.py --domain "federated learning" --limit 50

# Start the API
uvicorn src.api.main:app --reload --port 8000
```

---

## Eval thresholds

Every push to `main` runs the RAGAs evaluation pipeline. Build fails if any metric
drops below threshold.

| Metric | Threshold | What it measures |
|---|---|---|
| Faithfulness | ≥ 0.80 | Every claim traces back to a retrieved chunk |
| Answer relevance | ≥ 0.85 | The output actually addresses the query |
| Citation coverage | ≥ 0.90 | Claims link to real, verifiable sources |

---
## Why I built this

At the start of my own final year project, my idea approval took far longer than
it should have. Each week my supervisor pointed out that my ideas weren't
technically deep enough. I eventually figured out why: I was starting with
"what app can I build?" instead of "what problem hasn't been solved yet?"

Most FYP students make the same mistake. That question leads to CRUD applications,
dashboards, and management systems. Projects that work but lack research
contribution and rarely impress supervisors.

The students who produce strong FYPs start differently: they pick a research domain,
read papers until they find repeated limitations and open problems, and only then
decide what to build as a proof of concept. Almost no student knows this process
exists, let alone how to execute it. AI tools like ChatGPT make it worse: they
return shallow application ideas on demand, skipping the research foundation entirely.

This is validated by a guide written by a recent Westminster FYP graduate:

> "Do not start with the app. Start with the research gap. A good FYP is not just
> about building something that works. It is about showing that you understood a
> problem, studied existing work, identified a meaningful gap, proposed a solution,
> and evaluated it properly."

Fynd is built to give every student the starting point I had to figure out the
hard way.

## What I learned building this

- **Hybrid retrieval is non-negotiable.** BM25 catches exact technical terms
  ("LoRA", "FAISS") that vector search misses. Vector search catches paraphrased
  concepts that BM25 misses. Neither alone is sufficient.
- **Section-aware chunking changes retrieval quality fundamentally.** Research gaps
  live in Limitations and Future Work sections — naive character chunking buries them
  equally with the introduction.
- **Citation enforcement belongs in code, not prompts.** Telling an LLM to cite its
  sources is unreliable. Tracking chunk IDs through the pipeline and verifying them
  against output is not.
- **Evaluation is harder than building.** Faithfulness and answer relevance are
  different things. A grounded response can still be irrelevant. Measuring both
  separately is what makes the eval pipeline meaningful.