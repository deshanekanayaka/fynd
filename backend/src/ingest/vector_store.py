import logging
import chromadb
from config import CHROMA_COLLECTION_NAME, CHROMA_PATH

logger = logging.getLogger(__name__)


def get_collection() -> chromadb.Collection:
    """
    Initialises a persistent Chroma client and returns the fynd_chunks collection.
    PersistentClient saves to disk at CHROMA_PATH so data survives restarts.
    get_or_create_collection is safe to call repeatedly — won't wipe existing data.
    """
    # PersistentClient writes to disk — your chunks survive between runs.
    # In production this would be replaced by a Pinecone client — same interface.
    client = chromadb.PersistentClient(path=CHROMA_PATH)

    # We set embedding_function=None because we're providing our own vectors.
    # If we didn't, Chroma would try to embed the documents itself using its
    # default model — we don't want that, we want our own MiniLM vectors.
    collection = client.get_or_create_collection(
        name=CHROMA_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},  # cosine similarity, not Euclidean distance
    )

    return collection


def store_chunks(chunks: list[dict], collection: chromadb.Collection) -> None:
    """
    Takes embedded chunk dicts and writes them into Chroma.
    Each chunk must already have an 'embedding' field from embedder.py.
    """
    if not chunks:
        logger.warning("No chunks to store.")
        return

    # Chroma's .add() takes four parallel lists — they must be the same length
    # and correspond to each other by index.
    ids = []         # unique string ID per chunk
    embeddings = []  # the 384-number vector
    documents = []   # the raw text (returned when this chunk wins a search)
    metadatas = []   # section, priority, paper_id — filterable later

    for chunk in chunks:
        # Chroma requires unique IDs. We build ours from paper_id + chunk index
        # to guarantee no collisions across multiple papers.
        chunk_id = chunk["chunk_id"]

        ids.append(chunk_id)
        embeddings.append(chunk["embedding"])
        documents.append(chunk["text"])
        metadatas.append({
            "paper_id": chunk["paper_id"],
            "section": chunk["section"],
            "priority": chunk["section_priority"],
            "arxiv_id":  chunk["paper_id"],
        })

    # upsert instead of add — safe to run the pipeline multiple times.
    # If a chunk ID already exists, it updates rather than throwing a duplicate error.
    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )

    logger.info(f"Stored {len(chunks)} chunks in Chroma.")


def search(
    query_embedding: list[float],
    collection: chromadb.Collection,
    top_k: int = 10,
    section_filter: str | None = None,
) -> list[dict]:
    """
    Searches Chroma for the top_k chunks most similar to the query embedding.
    Optionally filters by section — e.g. section_filter="limitations".
    Returns a list of dicts with text, metadata, and distance score.
    """
    # where= is Chroma's metadata filter. Only applied when we want it.
    where = {"section": section_filter} if section_filter else None

    results = collection.query(
        query_embeddings=[query_embedding],  # list of one vector (Chroma expects a list)
        n_results=top_k,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    # Chroma returns results nested in a list-of-lists because it supports
    # multiple queries at once. We only sent one query, so we take [0].
    chunks_out = []
    for text, metadata, distance in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        chunks_out.append({
            "text": text,
            "metadata": metadata,
            "score": 1 - distance,  # convert cosine distance → similarity (1 = identical)
        })

    return chunks_out