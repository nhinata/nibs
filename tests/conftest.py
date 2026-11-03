import pytest

from nibs import page


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    """Keep the cache and the usage record of every test in its own directory."""
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.delenv("NIBS_LOG", raising=False)


@pytest.fixture
def site(monkeypatch):
    """A fake web: maps URL -> (content type, body) and counts fetches."""
    pages, calls = {}, []

    def fetch(url):
        calls.append(url)
        if url not in pages:
            raise page.urllib.error.URLError("not found")
        return pages[url]

    monkeypatch.setattr(page, "fetch", fetch)
    return pages, calls
