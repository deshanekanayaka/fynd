import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

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

CHUNK_SIZE = 512      # Target character count per chunk
CHUNK_OVERLAP = 50    # Characters repeated between consecutive chunks


def chunk_paper(paper: dict, pdf_text: str | None) -> list[dict]:
    """
    Given a paper dict and optional PDF text, return a list of chunks.
    Each chunk carries metadata so retrieval knows where it came from.
    """
    arxiv_id = paper["arxiv_id"]

    if pdf_text:
        sections = _detect_sections(pdf_text, arxiv_id)
    else:
        # No PDF — fall back to abstract as a single section
        logger.warning(f"[{arxiv_id}] No PDF text, falling back to abstract")
        sections = {"abstract": paper.get("abstract", "")}

    chunks = []
    for section_name, section_text in sections.items():
        if not section_text.strip():
            continue

        priority = _get_priority(section_name)
        section_chunks = _split_into_chunks(section_text)

        for position, chunk_text in enumerate(section_chunks):
            chunks.append({
                "chunk_id": f"{arxiv_id}_{section_name}_{position}",
                "paper_id": arxiv_id,
                "title": paper.get("title", ""),
                "section": section_name,
                "section_priority": priority,
                "text": chunk_text,
                "char_count": len(chunk_text),
                "position": position,
            })

    logger.info(f"[{arxiv_id}] Produced {len(chunks)} chunks across {len(sections)} sections")
    return chunks


def save_chunks(chunks: list[dict], arxiv_id: str, output_dir: Path) -> None:
    """Save chunks for a single paper to data/chunks/<arxiv_id>.json"""
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{arxiv_id.replace('/', '_')}.json"

    with open(output_path, "w") as f:
        json.dump(chunks, f, indent=2)

    logger.info(f"[{arxiv_id}] Saved {len(chunks)} chunks to {output_path}")


def _detect_sections(text: str, arxiv_id: str) -> dict[str, str]:
    """
    Split raw PDF text into named sections using regex heading detection.
    Returns a dict of {section_name: section_text}.
    Anything before the first recognised heading goes into 'body'.
    """
    # Match lines that look like section headings:
    # Optional number (e.g. "5"), then a known heading word, at start of line
    # re.IGNORECASE handles "LIMITATIONS", "Limitations", "limitations"
    # re.MULTILINE makes ^ match start of each line, not just start of string
    heading_pattern = re.compile(
        r"^(?:\d+\.?\s+)?(limitations|future work|discussion|conclusion[s]?|abstract|introduction)\s*$",
        re.IGNORECASE | re.MULTILINE
    )

    matches = list(heading_pattern.finditer(text))

    if not matches:
        # No recognisable headings found — treat everything as body text
        logger.warning(f"[{arxiv_id}] No section headings detected in PDF text")
        return {"body": text}

    sections = {}

    # Capture any text that appears before the first heading as 'body'
    if matches[0].start() > 0:
        preamble = text[:matches[0].start()].strip()
        if preamble:
            sections["body"] = preamble

    # For each heading, its section text runs until the next heading starts
    for i, match in enumerate(matches):
        section_name = match.group(1).lower().replace(" ", "_")
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        section_text = text[start:end].strip()
        sections[section_name] = section_text

    return sections


def _split_into_chunks(text: str) -> list[str]:
    """
    Split a section's text into overlapping chunks of ~CHUNK_SIZE characters.
    The last CHUNK_OVERLAP characters of each chunk are repeated at the
    start of the next, so sentences at boundaries aren't lost.
    """
    chunks = []
    start = 0

    while start < len(text):
        end = start + CHUNK_SIZE
        chunk = text[start:end]
        chunks.append(chunk)
        # Move forward by CHUNK_SIZE minus the overlap
        # This means the next chunk starts CHUNK_OVERLAP chars before this one ended
        start += CHUNK_SIZE - CHUNK_OVERLAP

    return chunks


def _get_priority(section_name: str) -> int:
    """Return the priority number for a section name. Body text gets lowest priority."""
    # Normalise to lowercase with underscores to match SECTION_PRIORITIES keys
    normalised = section_name.lower().replace(" ", "_")
    for keyword, (priority, _) in SECTION_PRIORITIES.items():
        if keyword in normalised:
            return priority
    return 6  # Default: body text