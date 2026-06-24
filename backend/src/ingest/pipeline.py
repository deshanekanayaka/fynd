import json
import logging
import argparse
from pathlib import Path
from fetch_papers import fetch_arxiv_papers, enrich_with_semantic_scholar

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Where raw papers land — relative to backend/
RAW_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"


def run_ingestion(query: str, max_results: int = 20, dry_run: bool = False) -> None:
    """
    Full ingestion pipeline: fetch from ArXiv → enrich with S2 → save as JSON.
    dry_run=True prints what would happen without writing any files.
    """
    logger.info(f"Starting ingestion: query='{query}', max_results={max_results}")

    # Step 1 — fetch from ArXiv
    papers = fetch_arxiv_papers(query, max_results)

    # Step 2 — enrich with Semantic Scholar
    papers = enrich_with_semantic_scholar(papers)

    if dry_run:
        # Print a summary of what would be saved — useful when tweaking the pipeline
        logger.info(f"DRY RUN — would save {len(papers)} papers:")
        for p in papers:
            logger.info(f"  {p['arxiv_id']} | {p['title'][:60]} | citations: {p['citation_count']}")
        return

    # Step 3 — save each paper as its own JSON file, named by ArXiv ID
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)  # creates data/raw/ if it doesn't exist

    saved = 0
    for paper in papers:
        output_path = RAW_DATA_DIR / f"{paper['arxiv_id']}.json"

        # Skip papers we've already fetched — don't re-download on repeated runs
        if output_path.exists():
            logger.info(f"Already exists, skipping: {paper['arxiv_id']}")
            continue

        with open(output_path, "w") as f:
            json.dump(paper, f, indent=2)

        saved += 1

    logger.info(f"Saved {saved} new papers to {RAW_DATA_DIR}")


if __name__ == "__main__":
    # This lets you run: python pipeline.py --domain "retrieval augmented generation" --limit 20
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", required=True, help="Search query / research domain")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    run_ingestion(query=args.domain, max_results=args.limit, dry_run=args.dry_run)