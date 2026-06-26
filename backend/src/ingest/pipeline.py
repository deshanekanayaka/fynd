import json
import logging
import argparse
from pathlib import Path
from tqdm.contrib.logging import logging_redirect_tqdm
from fetch_papers import fetch_arxiv_papers, enrich_with_semantic_scholar
from pdf_extractor import extract_pdf_text
from chunker import chunk_paper, save_chunks

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RAW_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
CHUNKS_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "chunks"


def run_ingestion(query: str, max_results: int = 20, dry_run: bool = False) -> None:
    """
    Full ingestion pipeline:
    fetch → enrich → save raw → extract PDF → chunk → save chunks
    dry_run=True logs what would happen without writing any files.
    """
    logger.info(f"Starting ingestion: query='{query}', max_results={max_results}")

    with logging_redirect_tqdm():
        papers = fetch_arxiv_papers(query, max_results)
        papers = enrich_with_semantic_scholar(papers)

    if dry_run:
        logger.info(f"DRY RUN — would save {len(papers)} papers:")
        for p in papers:
            logger.info(f"  {p['arxiv_id']} | {p['title'][:60]} | citations: {p['citation_count']}")
        return

    # Step 3 — save each paper as raw JSON
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    saved = 0
    for paper in papers:
        safe_id = paper["arxiv_id"].replace("/", "_")
        output_path = RAW_DATA_DIR / f"{safe_id}.json"

        if ".." in paper["arxiv_id"] or ".." in safe_id:
            logger.warning(f"Suspicious ID detected (contains '..'): {paper['arxiv_id']}, skipping")
            continue

        if not output_path.resolve().is_relative_to(RAW_DATA_DIR.resolve()):
            logger.warning(f"Unsafe path detected for ID {paper['arxiv_id']}, skipping")
            continue

        if output_path.exists():
            logger.info(f"[{paper['arxiv_id']}] Already exists, skipping raw save")
        else:
            with open(output_path, "w") as f:
                json.dump(paper, f, indent=2)
            saved += 1

    logger.info(f"Saved {saved} new papers to {RAW_DATA_DIR}")

    # Step 4 — extract PDF text and chunk each paper
    logger.info("Starting PDF extraction and chunking...")

    CHUNKS_DATA_DIR.mkdir(parents=True, exist_ok=True)

    chunked = 0
    for paper in papers:
        safe_id = paper["arxiv_id"].replace("/", "_")
        chunk_path = CHUNKS_DATA_DIR / f"{safe_id}.json"

        # Same path traversal guards as the raw-save step
        if ".." in paper["arxiv_id"] or ".." in safe_id:
            logger.warning(f"Suspicious ID detected (contains '..'): {paper['arxiv_id']}, skipping")
            continue

        if not chunk_path.resolve().is_relative_to(CHUNKS_DATA_DIR.resolve()):
            logger.warning(f"Unsafe chunk path detected for ID {paper['arxiv_id']}, skipping")
            continue

        if chunk_path.exists():
            logger.info(f"[{paper['arxiv_id']}] Chunks already exist, skipping")
            continue

        pdf_text = extract_pdf_text(paper)
        chunks = chunk_paper(paper, pdf_text)
        save_chunks(chunks, paper["arxiv_id"], CHUNKS_DATA_DIR)
        chunked += 1

    logger.info(f"Chunked {chunked} new papers to {CHUNKS_DATA_DIR}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fynd ingestion pipeline")
    parser.add_argument("--domain", required=True, help="Research domain to search")
    parser.add_argument("--limit", type=int, default=20, help="Max papers to fetch")
    parser.add_argument("--dry-run", action="store_true", help="Preview without saving")
    args = parser.parse_args()

    run_ingestion(
        query=args.domain,
        max_results=args.limit,
        dry_run=args.dry_run,
    )