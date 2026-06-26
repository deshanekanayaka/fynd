import sys
import types
from contextlib import contextmanager
from pathlib import Path
import pytest

# Ensure backend/src and backend/src/ingest are both importable
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "backend" / "src"
INGEST_PATH = SRC_PATH / "ingest"
for p in [str(SRC_PATH), str(INGEST_PATH)]:
    if p not in sys.path:
        sys.path.insert(0, p)

# Provide lightweight dummy modules for optional third-party deps so tests run offline
# without requiring installation.

def _ensure_module(name: str, attrs: dict | None = None):
    if name in sys.modules:
        return sys.modules[name]
    mod = types.ModuleType(name)
    if attrs:
        for k, v in attrs.items():
            setattr(mod, k, v)
    sys.modules[name] = mod
    return mod

# Dummy tqdm with passthrough tqdm() and a logging_redirect_tqdm context manager
_tqdm = _ensure_module("tqdm", {"tqdm": lambda it, **kw: it})
_tqdm_contrib = _ensure_module("tqdm.contrib")
@contextmanager
def _logging_redirect_tqdm():
    yield
_tqdm_logging = _ensure_module("tqdm.contrib.logging", {"logging_redirect_tqdm": _logging_redirect_tqdm})

# Dummy dotenv
_ensure_module("dotenv", {"load_dotenv": lambda *a, **k: None})

# Dummy semanticscholar client
class _DummyS2:
    def __init__(self, api_key=None):
        pass
    def get_paper(self, *a, **k):
        return None
_ensure_module("semanticscholar", {"SemanticScholar": _DummyS2})

# Minimal arxiv module so import works; tests will monkeypatch its classes
class _DummyClient:
    def results(self, search):
        return []
class _DummySearch:
    def __init__(self, *a, **k):
        pass
_ensure_module("arxiv", {"Client": _DummyClient, "Search": _DummySearch, "SortCriterion": types.SimpleNamespace(Relevance=0)})


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    """Speed up tests by disabling time.sleep calls in our modules."""
    import time
    monkeypatch.setattr(time, "sleep", lambda *args, **kwargs: None)
    yield


@pytest.fixture()
def tmp_raw_dir(tmp_path, monkeypatch):
    """Patch pipeline.RAW_DATA_DIR to a temporary directory for safe IO tests."""
    from ingest import pipeline
    raw_dir = tmp_path / "raw"
    monkeypatch.setattr(pipeline, "RAW_DATA_DIR", raw_dir)
    return raw_dir


@pytest.fixture()
def fake_arxiv_result_factory():
    """Factory to create fake arxiv result objects with required attributes."""
    from datetime import datetime, timezone

    class Author:
        def __init__(self, name):
            self.name = name

    class Result:
        def __init__(self, entry_id, title="A Paper", authors=None, summary="Abstract...",
                     published=None, pdf_url="http://arxiv.org/pdf/1234.pdf", primary_category="cs.AI"):
            self.entry_id = entry_id
            self.title = title
            self.authors = [Author(a) for a in (authors or ["Alice", "Bob"])]
            self.summary = summary
            self.published = published or datetime(2020, 5, 22, tzinfo=timezone.utc)
            self.pdf_url = pdf_url
            self.primary_category = primary_category

    return Result


@pytest.fixture()
def mock_arxiv(monkeypatch, fake_arxiv_result_factory):
    """Mock arxiv.Client().results(...) to yield our fake results."""
    class FakeClient:
        def results(self, search):
            # Yield is controlled per-test by setting attribute on this class
            yield from self._results

    fake_client = FakeClient()
    fake_client._results = []

    def fake_client_ctor(*args, **kwargs):
        return fake_client

    import arxiv
    monkeypatch.setattr(arxiv, "Client", fake_client_ctor)

    # Also patch arxiv.Search to a simple holder so constructing it doesn't fail
    class Search:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    monkeypatch.setattr(arxiv, "Search", Search)

    # Ensure SortCriterion.Relevance exists as used in code
    arxiv.SortCriterion = types.SimpleNamespace(Relevance=0)

    return fake_client, fake_arxiv_result_factory


@pytest.fixture()
def mock_semantic_scholar(monkeypatch):
    """Mock the module-level Semantic Scholar client used in fetch_papers."""
    from ingest import fetch_papers

    class FakeS2Paper:
        def __init__(self, citation_count=42, pdf_url="https://example.org/open.pdf"):
            self.citationCount = citation_count
            self.openAccessPdf = {"url": pdf_url}

    class FakeS2Client:
        def __init__(self):
            self.calls = []
        def get_paper(self, paper_id, fields=None):
            self.calls.append((paper_id, tuple(fields) if fields else None))
            return FakeS2Paper()

    fake_client = FakeS2Client()
    monkeypatch.setattr(fetch_papers, "sch", fake_client)
    return fake_client
