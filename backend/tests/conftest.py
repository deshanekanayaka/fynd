import sys
import types
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

# Dummy sentence_transformers — tests don't test embedding, so stub the whole module.
# We can't stub tqdm because sentence_transformers and huggingface_hub subclass it
# internally — the real tqdm package is installed and handles its own imports.
class _DummySentenceTransformer:
    def __init__(self, *a, **k):
        pass
    def encode(self, texts, **k):
        if isinstance(texts, str):
            return [0.0] * 384
        return [[0.0] * 384 for _ in texts]

_ensure_module("sentence_transformers", {"SentenceTransformer": _DummySentenceTransformer})

# Dummy dotenv
_ensure_module("dotenv", {
    "load_dotenv": lambda *a, **k: None,
    "dotenv_values": lambda *a, **k: {},
})

# Dummy chromadb — tests don't test vector storage
class _DummyCollection:
    def upsert(self, *a, **k): pass
    def query(self, *a, **k): return {"documents": [[]], "metadatas": [[]], "distances": [[]]}
    def count(self): return 0
    def peek(self, *a, **k): return {"documents": [], "metadatas": []}

class _DummyChromaClient:
    def get_or_create_collection(self, *a, **k): return _DummyCollection()
    def get_collection(self, *a, **k): return _DummyCollection()

_chromadb_mod = _ensure_module("chromadb")
_chromadb_mod.PersistentClient = lambda *a, **k: _DummyChromaClient()
_chromadb_mod.Collection = _DummyCollection
_ensure_module("chromadb.api", {"Collection": _DummyCollection})

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
            yield from self._results

    fake_client = FakeClient()
    fake_client._results = []

    def fake_client_ctor(*args, **kwargs):
        return fake_client

    import arxiv
    monkeypatch.setattr(arxiv, "Client", fake_client_ctor)

    class Search:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    monkeypatch.setattr(arxiv, "Search", Search)
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