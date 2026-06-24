from tqdm import tqdm
import arxiv
import time
import logging
from semanticscholar import SemanticScholar
from dotenv import load_dotenv
import os

load_dotenv()

# Set up logging so we can see what's happening when the script runs.
# AI pipelines fail silently without this — you need to know which paper failed and why.
logger = logging.getLogger(__name__)

# Initialise the Semantic Scholar client once, at module level.
# Passing the API key gives us a higher rate limit than anonymous requests.
sch = SemanticScholar(api_key=os.getenv("SEMANTIC_SCHOLAR_API_KEY"))


def fetch_arxiv_papers(query: str, max_results: int = 20) -> list[dict]:
    """
    Search ArXiv and return a list of paper metadata dicts.
    Each dict contains everything ArXiv gives us for that paper.
    """
    client = arxiv.Client()  # Default client — handles rate limiting and retries for us

    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance  # Most relevant papers first, not newest
    )

    papers = []

    for result in client.results(search):
        # result.entry_id looks like "https://arxiv.org/abs/2005.11401v4"
        # We extract just "2005.11401" — the clean ArXiv ID we'll use everywhere
        arxiv_id = result.entry_id.split("/abs/")[-1].split("v")[0]

        paper = {
            "arxiv_id": arxiv_id,
            "title": result.title,
            # result.authors is a list of Author objects — we pull just the name string
            "authors": [author.name for author in result.authors],
            "abstract": result.summary,
            "published": result.published.isoformat(),  # datetime → "2020-05-22T00:00:00+00:00"
            "pdf_url": result.pdf_url,
            "primary_category": result.primary_category,
            # Semantic Scholar enrichment fields — populated in the next step
            "citation_count": None,
            "s2_pdf_url": None,
        }
        papers.append(paper)

    logger.info(f"Fetched {len(papers)} papers from ArXiv for query: '{query}'")
    return papers


def enrich_with_semantic_scholar(papers: list[dict]) -> list[dict]:
    """
    For each paper, hit Semantic Scholar using its ArXiv ID to get
    citation count and an open-access PDF URL if available.
    Mutates papers in place and returns the same list.
    """
    for paper in tqdm(papers, desc="Enriching with Semantic Scholar", unit="paper"):
            try:
                s2_paper = sch.get_paper(
                    f"ArXiv:{paper['arxiv_id']}",
                    fields=["citationCount", "openAccessPdf"]
                )

                if s2_paper:
                    paper["citation_count"] = s2_paper.citationCount
                    paper["s2_pdf_url"] = (
                        s2_paper.openAccessPdf.get("url")
                        if s2_paper.openAccessPdf
                        else None
                    )

            except Exception as e:
                logger.warning(f"Semantic Scholar lookup failed for {paper['arxiv_id']}: {e}")

            time.sleep(1)

    logger.info(f"Enrichment complete for {len(papers)} papers")
    return papers