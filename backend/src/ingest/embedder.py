import logging
from sentence_transformers import SentenceTransformer
from config import EMBEDDING_MODEL

logger = logging.getLogger(__name__)


def load_model() -> SentenceTransformer:
    # Downloads the model on first run, then caches it locally.
    # "all-MiniLM-L6-v2" is the model name from HuggingFace Hub.
    logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
    return SentenceTransformer(EMBEDDING_MODEL)


def embed_chunks(chunks: list[dict], model: SentenceTransformer) -> list[dict]:
    """
    Takes chunk dicts from the chunker, adds an 'embedding' field to each.
    Returns the same chunks with embeddings attached.
    """
    if not chunks:
        return []

    # Pull just the text out of each chunk — that's what the model embeds.
    # The rest of the chunk dict (section, priority, paper_id etc.) stays untouched.
    texts = [chunk["text"] for chunk in chunks]

    logger.info(f"Embedding {len(texts)} chunks...")

    # .encode() takes a list of strings, returns a numpy array of shape
    # (num_chunks, 384) — one row of 384 numbers per chunk.
    # convert_to_list=True turns numpy arrays into plain Python lists,
    # which Chroma expects when we pass embeddings manually.
    embeddings = model.encode(texts, convert_to_numpy=False, show_progress_bar=True)

    # Zip the original chunk dicts with their corresponding embedding vectors.
    # We're attaching the vector back onto the chunk so vector_store.py
    # receives everything it needs in one place.
    for chunk, embedding in zip(chunks, embeddings):
        chunk["embedding"] = embedding.tolist()  # [0.23, -0.87, 0.41, ...]

    logger.info("Embedding complete.")
    return chunks


def embed_query(query: str, model: SentenceTransformer) -> list[float]:
    """
    Embeds a single query string at search time.
    Returns a flat list of 384 floats — same space as the chunk vectors.
    """
    # encode() can take a single string or a list.
    # We pass a list of one and take [0] to get a flat vector back.
    return model.encode([query], convert_to_numpy=False)[0].tolist()