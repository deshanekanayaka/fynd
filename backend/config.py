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
SECTION_PRIORITY = ["limitations", "future work", "conclusion", "abstract"]

CHROMA_PATH = str(Path(__file__).resolve().parent / "data" / "chroma")
CHROMA_COLLECTION_NAME = "fynd_chunks"