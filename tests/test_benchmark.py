import json
import sys
from pathlib import Path

import pytest

from nibs import page

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "benchmark"))

import compare  # noqa: E402
import fetch_pages  # noqa: E402
import select_pages  # noqa: E402


@pytest.mark.parametrize(
    "source, url",
    [
        ("self.base_url = 'https://a.dev/docs/'", "https://a.dev/docs/"),
        ("self.base_urls = [\n  'https://a.dev/x/',\n  'https://a.dev/y/'\n]", "https://a.dev/x/"),
        ("self.base_urls = %w[\n  https://a.dev/x/\n  https://a.dev/y/\n]", "https://a.dev/x/"),
        ("version '3' do\n  self.base_url = \"https://a.dev/#{self.version}/\"\nend\n"
         "version '2' do\n  self.base_url = \"https://a.dev/#{self.version}/\"\nend", "https://a.dev/3/"),
        ("self.release = '1.2'\nself.base_url = \"https://a.dev/#{release}/\"", "https://a.dev/1.2/"),
        ("self.base_url = 'http://localhost:8000/docs/'", None),
        ("self.base_url = \"https://a.dev/#{unknown}/\"", None),
        ("title = self.base_url.path", None),
        ("# self.base_url = 'https://old.dev/'\nself.base_url = 'https://new.dev/'", "https://new.dev/"),
    ],
)
def test_base_url_of_a_scraper(source, url):
    assert select_pages.base_url(source) == url


def test_links_under_stay_in_the_directory_without_the_page_itself():
    html = '<a href="b.html#x">b</a><a href="a.html">self</a><a href="/out">o</a><a href="c/d">d</a>'
    assert select_pages.links_under("https://x.dev/docs/a.html", html) == [
        "https://x.dev/docs/b.html",
        "https://x.dev/docs/c/d",
    ]


def test_links_of_an_address_without_a_path_stay_on_its_host():
    html = '<a href="/docs">d</a><a href="https://github.com/x">o</a>'
    assert select_pages.links_under("https://x.dev", html) == ["https://x.dev/docs"]


def test_a_slash_in_the_query_does_not_move_the_directory():
    html = '<a href="b">b</a>'
    assert select_pages.links_under("https://x.dev/docs/a?from=/c/d", html) == ["https://x.dev/docs/b"]


def test_a_checkout_at_another_commit_is_refused(monkeypatch):
    monkeypatch.setattr(select_pages, "checkout_commit", lambda _: "other")
    config = {"docs": {"devdocs_commit": "pinned", "count": 1}, "seed": 1}
    with pytest.raises(SystemExit, match="not at the commit"):
        select_pages.select_docs(config, "devdocs")


def test_the_same_seed_picks_the_same_page(monkeypatch):
    html = "".join(f'<a href="{n}.html">p</a>' for n in range(50))
    monkeypatch.setattr(select_pages, "read_start_page", lambda url: (url, html))
    picks = {select_pages.pick_page(1, "Product", "https://x.dev/") for _ in range(5)}
    assert len(picks) == 1


def test_a_start_page_that_cannot_be_read_stays_in_the_set(monkeypatch):
    def fail(_url):
        raise OSError("refused")

    monkeypatch.setattr(select_pages, "read_start_page", fail)
    assert select_pages.pick_page(1, "Product", "https://x.dev/") == "https://x.dev/"


class FakeOpener:
    """Answers with HTML in Latin-1, which only the charset it declares can decode."""

    def open(self, req, timeout=None):
        if req.full_url.endswith(".md"):
            raise page.urllib.error.URLError("no such page")
        body = "<h1>Café</h1><p>Text</p>".encode("latin-1")
        return fetch_pages.Answer("text/html; charset=latin-1", req.full_url, body)


def recorded(tmp_path, monkeypatch, url="https://x.dev/a"):
    monkeypatch.setattr(page, "_OPENER", fetch_pages.Recording(FakeOpener(), tmp_path))
    return page._download(url)


def test_kept_answers_read_the_same_without_a_network(tmp_path, monkeypatch):
    live = recorded(tmp_path, monkeypatch)
    monkeypatch.setattr(page, "_OPENER", fetch_pages.Saved(tmp_path))
    assert page._download("https://x.dev/a") == live
    assert "Café" in live[0]


def test_an_address_outside_the_set_is_an_error_like_a_failed_request(tmp_path, monkeypatch):
    monkeypatch.setattr(page, "_OPENER", fetch_pages.Saved(tmp_path))
    with pytest.raises(page.FETCH_ERRORS):
        page._download("https://x.dev/never-asked")


def changed_checkout(tmp_path):
    """A copy of nibs' src whose reading adds a heading to every page."""
    head = tmp_path / "head"
    (head / "nibs").mkdir(parents=True)
    for source in (ROOT / "src" / "nibs").glob("*.py"):
        text = source.read_text(encoding="utf-8")
        if source.name == "page.py":
            text += "\n_old_html_to_text = html_to_text\nhtml_to_text = lambda html: _old_html_to_text(html) + '\\n\\n# New\\n'\n"
        (head / "nibs" / source.name).write_text(text, encoding="utf-8")
    return head


def test_compare_runs_each_version_and_shows_what_changed(tmp_path, monkeypatch):
    url = "https://x.dev/a"
    recorded(tmp_path, monkeypatch, url)
    (tmp_path / "pages.jsonl").write_text(json.dumps({"group": "docs", "url": url, "error": None}) + "\n")
    head = changed_checkout(tmp_path)
    pages = [{"group": "docs", "url": url}]
    old = compare.run_version(tmp_path, ROOT / "src", tmp_path / "old.json")
    new = compare.run_version(tmp_path, head, tmp_path / "new.json")
    text = compare.report(pages, old, new)
    assert "| docs | 1 | 0 | html 1 | 1 |" in text
    assert "| 1 | 0 |" in text  # one page gained a heading, none lost one
    assert "+# New" in text


def test_a_nibs_in_the_working_directory_is_not_the_one_compared(tmp_path, monkeypatch):
    url = "https://x.dev/a"
    recorded(tmp_path, monkeypatch, url)
    (tmp_path / "pages.jsonl").write_text(json.dumps({"group": "docs", "url": url, "error": None}) + "\n")
    head = changed_checkout(tmp_path)
    monkeypatch.chdir(ROOT / "src")
    new = compare.run_version(tmp_path, head, tmp_path / "new.json")
    assert ["New"] == [title for _, title, _ in new[url]["sections"] if title == "New"]


@pytest.mark.parametrize(
    "old, new, shown",
    [
        ({"sections": [[1, "A #", 1]]}, {"sections": [[1, "A", 1]]}, "+# A (1 lines)"),
        ({"sections": [[1, "A", 1]]}, {"sections": [[1, "A", 2]]}, "+# A (2 lines)"),
        ({"source": "html"}, {"source": "md"}, "+md"),
    ],
)
def test_a_page_with_the_same_text_can_still_have_changed(old, new, shown):
    pages = [{"group": "docs", "url": "u"}]
    result = {"text": "same", "source": "html", "sections": []}
    text = compare.report(pages, {"u": {**result, **old}}, {"u": {**result, **new}})
    assert "## docs: u" in text
    assert shown in text


def test_a_different_reason_for_a_page_unread_in_both_is_listed():
    pages = [{"group": "docs", "url": "u"}]
    text = compare.report(pages, {"u": {"error": "one"}}, {"u": {"error": "two"}})
    assert "-one" in text and "+two" in text


def test_the_fence_of_a_diff_is_longer_than_any_backticks_in_it():
    pages = [{"group": "docs", "url": "u"}]
    result = {"source": "html", "sections": []}
    old = {"u": {**result, "text": "`````\ncode\n`````"}}
    new = {"u": {**result, "text": "`````\nother\n`````"}}
    lines = compare.report(pages, old, new).splitlines()
    assert "``````diff" in lines and lines[-1] == "``````"


def test_a_page_a_version_can_no_longer_read_is_reported_as_changed():
    pages = [{"group": "docs", "url": "u"}]
    old = {"u": {"text": "# A\n", "source": "html", "sections": [[1, "A", 1]]}}
    new = {"u": {"error": "boom"}}
    text = compare.report(pages, old, new)
    assert "| docs | 1 | 1 |  | 1 |" in text
    assert "- 1: boom" in text
    assert "-# A" in text


def test_a_page_that_cannot_be_read_counts_in_the_characters():
    pages = [{"group": "docs", "url": "u"}, {"group": "docs", "url": "v"}]
    same = {"text": "x" * 100, "source": "html", "sections": []}
    old = {"u": same, "v": same}
    new = {"u": same, "v": {"error": "boom"}}
    assert "| -50.0% |" in compare.report(pages, old, new)


def test_reasons_are_reported_for_each_group():
    pages = [{"group": "docs", "url": "u"}, {"group": "general", "url": "v"}]
    results = {"u": {"error": "boom"}, "v": {"error": "boom"}}
    text = compare.report(pages, results, results)
    assert "Unread in docs:\n\n- 1: boom" in text
    assert "Unread in general:\n\n- 1: boom" in text


def test_a_repeated_heading_counts_as_added():
    pages = [{"group": "docs", "url": "u"}]
    old = {"u": {"text": "# A\n", "source": "html", "sections": [[1, "A", 1]]}}
    new = {"u": {"text": "# A\n# A\n", "source": "html", "sections": [[1, "A", 1], [1, "A", 1]]}}
    assert "| 1 | 0 |" in compare.report(pages, old, new)


def test_a_directory_without_nibs_is_refused(tmp_path, capfd):
    with pytest.raises(SystemExit):
        compare.run_version(tmp_path, tmp_path, tmp_path / "out.json")
    assert "nibs came from" in capfd.readouterr().err


def test_a_directory_above_the_src_directory_is_refused(tmp_path, capfd):
    with pytest.raises(SystemExit):
        compare.run_version(tmp_path, ROOT, tmp_path / "out.json")
    assert "nibs came from" in capfd.readouterr().err


def test_a_version_that_fails_on_a_page_is_recorded_for_that_page(tmp_path, monkeypatch):
    url = "https://x.dev/a"
    recorded(tmp_path, monkeypatch, url)
    (tmp_path / "pages.jsonl").write_text(json.dumps({"group": "docs", "url": url, "error": None}) + "\n")
    head = changed_checkout(tmp_path)
    with (head / "nibs" / "page.py").open("a", encoding="utf-8") as file:
        file.write("\ndef sections(text):\n    raise ValueError('broken')\n")
    assert compare.run_version(tmp_path, head, tmp_path / "new.json") == {url: {"error": "broken"}}
