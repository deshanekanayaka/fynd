import io
import logging
import requests
import pdfplumber

logger = logging.getLogger(__name__)

# Maximum PDF size we'll process — 50MB is generous for an academic paper
MAX_PDF_BYTES = 50 * 1024 * 1024


def extract_pdf_text(paper: dict) -> str | None:
    """
    Attempt to download and extract full text from a paper's PDF.
    Tries pdf_url first, then s2_pdf_url as fallback.
    Returns the full text as a single string, or None if both fail.
    """
    urls_to_try = [
        paper.get("pdf_url"),
        paper.get("s2_pdf_url"),
    ]
    urls_to_try = [url for url in urls_to_try if url]

    for url in urls_to_try:
        text = _download_and_extract(url, paper["arxiv_id"])
        if text:
            return text

    logger.warning(f"[{paper['arxiv_id']}] PDF extraction failed for all URLs")
    return None


def _download_and_extract(url: str, arxiv_id: str) -> str | None:
    """
    Download a PDF from a URL and extract its text.
    Streams the response incrementally and enforces a MAX_PDF_BYTES limit.
    Returns extracted text string, or None if anything goes wrong.
    """
    try:
        response = requests.get(url, timeout=30, stream=True)
        response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if "pdf" not in content_type.lower():
            logger.warning(f"[{arxiv_id}] URL did not return a PDF: {content_type}")
            return None

        # Read response incrementally to avoid loading huge files into memory
        # Stop and abort if the PDF exceeds MAX_PDF_BYTES
        chunks = []
        total_bytes = 0
        for chunk in response.iter_content(chunk_size=8192):
            total_bytes += len(chunk)
            if total_bytes > MAX_PDF_BYTES:
                logger.warning(f"[{arxiv_id}] PDF exceeded {MAX_PDF_BYTES} bytes, aborting")
                return None
            chunks.append(chunk)

        pdf_bytes = io.BytesIO(b"".join(chunks))

        # Extract text page by page using word-level extraction.
        # x_tolerance_ratio=0.15 sets the space-detection threshold to 15% of
        # font size — this correctly handles LaTeX-generated ArXiv PDFs where
        # character gaps are smaller than the default fixed 3px tolerance.
        # See DECISIONS.md ADR-001 for full context.
        pages_text = []
        with pdfplumber.open(pdf_bytes) as pdf:
            for page in pdf.pages:
                words = page.extract_words(x_tolerance_ratio=0.15, y_tolerance=3)
                if not words:
                    continue

                lines = []
                current_line = []
                current_top = None

                for word in words:
                    word_top = round(word["top"])

                    if current_top is None:
                        current_top = word_top

                    if abs(word_top - current_top) > 5:
                        lines.append(" ".join(current_line))
                        current_line = []
                        current_top = word_top

                    current_line.append(word["text"])

                if current_line:
                    lines.append(" ".join(current_line))

                pages_text.append("\n".join(lines))

        full_text = "\n".join(pages_text)

        if not full_text.strip():
            logger.warning(f"[{arxiv_id}] PDF downloaded but extracted no text")
            return None

        logger.info(f"[{arxiv_id}] Extracted {len(full_text)} characters from PDF")
        return full_text

    except requests.exceptions.Timeout:
        logger.error(f"[{arxiv_id}] PDF download timed out: {url}")
        return None
    except requests.exceptions.HTTPError as e:
        logger.error(f"[{arxiv_id}] HTTP {e.response.status_code} downloading PDF: {url}")
        return None
    except Exception as e:
        logger.error(f"[{arxiv_id}] Unexpected error extracting PDF: {e}")
        return None