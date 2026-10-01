"""Step 04 of ingestion: run the three steps and save a Snapshot to disk.

Steps 01, 02, and 03 each do one thing and keep no files. This step is the only one
that writes. It asks arXiv for papers in a date range, reads each PDF, splits each
paper into sentences, and saves three files per paper.

The Snapshot is a set of local files for Phase 0, one directory per paper:

    backend/data/<phrase-slug>/<arxiv_id>/paper.json      the Paper Record
    backend/data/<phrase-slug>/<arxiv_id>/text.txt        the Paper Text
    backend/data/<phrase-slug>/<arxiv_id>/sentences.json  the sentences, in order

The collection date goes in the Paper Record, because an Untouched Verdict is only
true as of the date the Snapshot was gathered.
"""

import argparse
import json
import re
from datetime import date
from pathlib import Path

from src.ingest.fetch_papers import fetch_papers
from src.ingest.pdf_extractor import extract_paper_text
from src.ingest.sentence_splitter import split_sentences

# Relative to the backend folder, which is where you run the command from.
DEFAULT_OUT = Path("data")

PAPER_FILE = "paper.json"
TEXT_FILE = "text.txt"
SENTENCES_FILE = "sentences.json"


def _slug(phrase: str) -> str:
    """Turn a search phrase into a safe directory name: "Federated Learning" -> "federated-learning"."""

    lowered = phrase.lower()
    # Anything that is not a letter or a digit becomes a hyphen, so a phrase with a
    # slash or a colon in it cannot create a directory we did not mean to create.
    hyphenated = re.sub(r"[^a-z0-9]+", "-", lowered)
    return hyphenated.strip("-")


def _is_done(paper_dir: Path) -> bool:
    """True when all three files of one paper already sit on disk.

    All three, not any one. A run that died between writing the text and writing the
    sentences leaves a half finished paper, and a half finished paper has to be redone.
    """

    for name in (PAPER_FILE, TEXT_FILE, SENTENCES_FILE):
        if not (paper_dir / name).exists():
            return False
    return True


def _save_paper(paper_dir: Path, record: dict, text: str, sentences: list[str]) -> None:
    """Write the three files of one paper.

    The text and the sentences go first, and the Paper Record goes last. _is_done
    reads all three names, so the order does not matter for the skip test, but writing
    the record last keeps the directory honest if the disk fills up halfway.
    """

    paper_dir.mkdir(parents=True, exist_ok=True)
    (paper_dir / TEXT_FILE).write_text(text, encoding="utf-8")
    (paper_dir / SENTENCES_FILE).write_text(
        json.dumps(sentences, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (paper_dir / PAPER_FILE).write_text(
        json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def run_pipeline(
    phrase: str,
    start: str,
    end: str,
    max_results: int = 50,
    out_dir=DEFAULT_OUT,
    force: bool = False,
    fetch=fetch_papers,
    extract=extract_paper_text,
    split=split_sentences,
) -> dict:
    """Collect a Snapshot for one phrase and one date range. Returns the counts.

    The three steps arrive as arguments so a test can replace them with fakes and
    never touch the network. The real functions are the defaults.
    """

    snapshot_dir = Path(out_dir) / _slug(phrase)
    collected_on = date.today().isoformat()

    records = fetch(phrase, start, end, max_results=max_results)

    saved = 0
    skipped = 0
    failed = 0

    for record in records:
        paper_dir = snapshot_dir / record["arxiv_id"]

        # A rerun after a crash should cost no downloads. --force redoes everything,
        # which is what you want after changing the extractor or the splitter.
        if _is_done(paper_dir) and not force:
            skipped += 1
            continue

        # One bad paper must not end the run. A scanned PDF gives no text and raises,
        # and a Snapshot of 49 good papers out of 50 is still a useful Snapshot. The
        # count below is what tells you whether one failure became twenty.
        try:
            text = extract(record["pdf_url"])
            sentences = split(text)
        except Exception as error:
            print(f"FAILED {record['arxiv_id']}: {error}")
            failed += 1
            # Under --force the paper can already hold files from an earlier run, and
            # they are now older than the code that made them. We keep them, because
            # deleting them would lose a good paper to one timeout. A later run without
            # --force skips this directory, so the age has to be said out loud here.
            if _is_done(paper_dir):
                print(f"  kept the older files in {paper_dir}. Rerun with --force.")
            continue

        full_record = dict(record)
        full_record["collected_on"] = collected_on
        full_record["sentence_count"] = len(sentences)
        _save_paper(paper_dir, full_record, text, sentences)
        saved += 1
        print(f"Saved {record['arxiv_id']} ({len(sentences)} sentences)")

    print(
        f"Snapshot at {snapshot_dir}: {saved} saved, {skipped} skipped, {failed} failed"
    )
    return {"saved": saved, "skipped": skipped, "failed": failed, "dir": snapshot_dir}


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(
        description="Collect a Snapshot of arXiv papers for one phrase and date range."
    )
    parser.add_argument("phrase", help='a phrase to find in the abstract, such as "federated learning"')
    parser.add_argument("start", help="first day of the window, as YYYY-MM-DD")
    parser.add_argument("end", help="last day of the window, as YYYY-MM-DD, included in full")
    parser.add_argument("--max-results", type=int, default=50, help="how many papers to ask for")
    parser.add_argument("--out", default=DEFAULT_OUT, help="where to write the Snapshot")
    parser.add_argument(
        "--force",
        action="store_true",
        help="redo papers that already have all three files",
    )
    args = parser.parse_args(argv)

    run_pipeline(
        args.phrase,
        args.start,
        args.end,
        max_results=args.max_results,
        out_dir=args.out,
        force=args.force,
    )


if __name__ == "__main__":
    main()
