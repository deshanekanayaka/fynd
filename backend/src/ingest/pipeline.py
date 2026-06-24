import json
import logging
import argparse
from pathlib import Path
from tqdm.contrib.logging import logging_redirect_tqdm
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
    print(f"Starting ingestion: query='{query}', max_results={max_results}")

    with logging_redirect_tqdm():
        # Step 1 — fetch from ArXiv
        papers = fetch_arxiv_papers(query, max_results)

        # Step 2 — enrich with Semantic Scholar
        papers = enrich_with_semantic_scholar(papers)

    if dry_run:
        print(f"DRY RUN — would save {len(papers)} papers:")
        for p in papers:
            print(f"  {p['arxiv_id']} | {p['title'][:60]} | citations: {p['citation_count']}")
        return

    # Step 3 — save each paper as its own JSON file, named by ArXiv ID
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)  # creates data/raw/ if it doesn't exist

    saved = 0
    for paper in papers:
        # Sanitize the arxiv_id before using it as a filename.
        # Even though fetch_papers already sanitizes, we do it again here defensively —
        # pipeline.py shouldn't trust that its inputs are always coming from fetch_papers.
        safe_id = paper["arxiv_id"].replace("/", "_")
        output_path = RAW_DATA_DIR / f"{safe_id}.json"

        # Verify the resolved path stays inside RAW_DATA_DIR.
        # This guards against any path traversal if an ID somehow contains "../"
        if not output_path.resolve().is_relative_to(RAW_DATA_DIR.resolve()):
            print(f"WARNING: Unsafe path detected for ID {paper['arxiv_id']}, skipping")
            continue

        # Skip papers we've already fetched — don't re-download on repeated runs
        if output_path.exists():
            print(f"Already exists, skipping: {paper['arxiv_id']}")
            continue

        with open(output_path, "w") as f:
            json.dump(paper, f, indent=2)

        saved += 1

    print(f"Saved {saved} new papers to {RAW_DATA_DIR}")


if __name__ == "__main__":
    # This lets you run: python pipeline.py --domain "retrieval augmented generation" --limit 20
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", required=True, help="Search query / research domain")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    run_ingestion(query=args.domain, max_results=args.limit, dry_run=args.dry_run)