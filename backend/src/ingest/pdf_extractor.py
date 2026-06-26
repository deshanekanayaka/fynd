import io
import logging
import requests
import pdfplumber

logger = logging.getLogger(__name__)


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
    Returns extracted text string, or None if anything goes wrong.
    """
    try:
        response = requests.get(url, timeout=30, stream=True)
        response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if "pdf" not in content_type.lower():
            logger.warning(f"[{arxiv_id}] URL did not return a PDF: {content_type}")
            return None

        pdf_bytes = io.BytesIO(response.content)

        # Extract text page by page using word-level extraction for better spacing
        pages_text = []
        with pdfplumber.open(pdf_bytes) as pdf:
            for page in pdf.pages:
                # extract_words returns individual word bounding boxes
                # x_tolerance=3, y_tolerance=3 are the defaults — words further
                # apart than 3 points get treated as separate words
                words = page.extract_words(x_tolerance_ratio=0.15, y_tolerance=3)
                if not words:
                    continue

                lines = []
                current_line = []
                current_top = None

                for word in words:
                    # y position of word on page — words on the same line
                    # have the same (or very close) 'top' value
                    word_top = round(word["top"])

                    if current_top is None:
                        current_top = word_top

                    # If this word is more than 5 points below the current line,
                    # it's a new line — flush the current line and start fresh
                    if abs(word_top - current_top) > 5:
                        lines.append(" ".join(current_line))
                        current_line = []
                        current_top = word_top

                    current_line.append(word["text"])

                # Don't forget the last line
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