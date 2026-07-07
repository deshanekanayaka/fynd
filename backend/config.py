from pathlib import Path

# --- Chunking ---
CHUNK_SIZE = 512          # Max characters per chunk
CHUNK_OVERLAP = 50        # Characters shared between adjacent chunks

# --- Retrieval ---
TOP_K_RETRIEVAL = 20      # Candidates returned before reranking
TOP_K_RERANK = 5          # Final results returned after reranking

# --- Models ---
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
LLM_MODEL = "gemini-1.5-flash"    # Free tier, fast, good reasoning

# --- Eval thresholds ---
FAITHFULNESS_THRESHOLD = 0.80
RELEVANCE_THRESHOLD = 0.85
CITATION_THRESHOLD = 0.90

# --- Ingestion ---
ARXIV_MAX_RESULTS = 100

# Maps section heading keywords to a priority number and canonical name
# Lower number = higher priority = more likely to contain research gaps
SECTION_PRIORITIES = {
    "limitations":   (1, "limitations"),
    "future_work":   (2, "future_work"),
    "discussion":    (2, "discussion"),
    "conclusion":    (3, "conclusion"),
    "conclusions":   (3, "conclusion"),
    "abstract":      (4, "abstract"),
    "introduction":  (5, "introduction"),
}

CHROMA_PATH = str(Path(__file__).resolve().parent / "data" / "chroma")
CHROMA_COLLECTION_NAME = "fynd_chunks"