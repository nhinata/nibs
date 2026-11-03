import http.client
import json
import time

import pytest

from nibs import cache, cli, page

DOC = "\n".join([
    "# Guide",
    "intro",
    "## Install",
    "pip install it",
    "```sh",
    "# not a heading, a shell comment",
    "```",
    "## Usage",
    "run it",
    "### Flags",
    "--max",
])
HTML_URL = "https://example.com/guide"


def run(capsys, *argv):
    status = cli.main(list(argv))
    out = capsys.readouterr()
    return status, out.out, out.err


def test_toc_lists_headings_but_not_lines_inside_code_fences(site, capsys):
    pages, _ = site
    pages["https://example.com/a.md"] = ("text/markdown", DOC)
    _, out, _ = run(capsys, "toc", "https://example.com/a.md")
    assert "4 headings" in out
    assert "shell comment" not in out


def test_section_by_number_and_by_heading_text_ends_at_the_next_heading_of_its_level(site, capsys):
    pages, _ = site
    pages["https://example.com/a.md"] = ("text/markdown", DOC)
    _, by_number, _ = run(capsys, "section", "https://example.com/a.md", "3")
    _, by_text, _ = run(capsys, "section", "https://example.com/a.md", "usage")
    assert by_number == by_text
    assert by_text.startswith("## Usage") and "--max" in by_text and "pip install" not in by_text


def test_a_heading_that_matches_nothing_fails_and_says_where_to_look(site, capsys):
    pages, _ = site
    pages["https://example.com/a.md"] = ("text/markdown", DOC)
    status, out, err = run(capsys, "section", "https://example.com/a.md", "nowhere")
    assert status == 1 and out == "" and "nibs toc" in err


def test_html_page_uses_the_markdown_the_site_serves_at_url_plus_md(site, capsys):
    pages, _ = site
    pages[HTML_URL] = ("text/html", "<html><body><h1>From HTML</h1></body></html>")
    pages[HTML_URL + ".md"] = ("text/markdown", DOC)
    _, out, _ = run(capsys, "toc", HTML_URL)
    assert "Guide" in out and "From HTML" not in out


def test_html_without_markdown_is_split_by_its_headings_without_scripts_or_navigation(site, capsys):
    pages, _ = site
    pages[HTML_URL] = ("text/html", "<html><body><nav><h2>Menu</h2></nav><h1>Title</h1><p>body</p>"
                                    "<script>var x = 1;</script><h2>Part</h2><p>more</p></body></html>")
    _, out, _ = run(capsys, "section", HTML_URL, "Title")
    assert out.split() == ["#", "Title", "body", "##", "Part", "more"]


def test_control_characters_from_the_page_are_not_printed(site, capsys):
    pages, _ = site
    pages["https://example.com/a.md"] = ("text/markdown", "# T\x1b[2Jitle\nok\x07")
    _, out, _ = run(capsys, "section", "https://example.com/a.md", "1")
    assert "\x1b" not in out and "\x07" not in out


def test_a_page_without_headings_says_it_may_need_javascript(site, capsys):
    pages, _ = site
    pages[HTML_URL] = ("text/html", '<html><body><div id="root"></div><script src="app.js"></script></body></html>')
    _, toc, _ = run(capsys, "toc", HTML_URL)
    status, _, err = run(capsys, "section", HTML_URL, "1")
    assert "JavaScript" in toc
    assert status == 1 and "JavaScript" in err


def test_commands_on_the_same_page_fetch_it_once(site, capsys):
    pages, calls = site
    pages["https://example.com/a.md"] = ("text/markdown", DOC)
    run(capsys, "toc", "https://example.com/a.md")
    run(capsys, "section", "https://example.com/a.md", "2")
    run(capsys, "find", "https://example.com/a.md", "install")
    assert calls == ["https://example.com/a.md"]


def test_a_cached_page_is_fetched_again_after_it_expires(site, capsys, monkeypatch):
    pages, calls = site
    pages["https://example.com/a.md"] = ("text/markdown", DOC)
    run(capsys, "toc", "https://example.com/a.md")
    later = time.time() + cache.TTL_SECONDS + 1
    monkeypatch.setattr(cache.time, "time", lambda: later)
    run(capsys, "toc", "https://example.com/a.md")
    assert len(calls) == 2


def test_find_prints_matches_under_their_section(site, capsys):
    pages, _ = site
    pages["https://example.com/a.md"] = ("text/markdown", DOC)
    _, out, _ = run(capsys, "find", "https://example.com/a.md", "^run")
    assert out == "## Usage\n  run it\n"


def test_stats_compares_what_was_printed_with_reading_each_page_whole(site, capsys, tmp_path, monkeypatch):
    pages, _ = site
    pages["https://example.com/a.md"] = ("text/markdown", DOC)
    log = tmp_path / "log.jsonl"
    monkeypatch.setenv("NIBS_LOG", str(log))
    run(capsys, "section", "https://example.com/a.md", "2")
    run(capsys, "section", "https://example.com/a.md", "3")
    rows = [json.loads(line) for line in log.read_text().splitlines()]
    _, out, _ = run(capsys, "stats")
    assert "2 runs over 1 page-days" in out
    assert f"{len(DOC):,}" in out and sum(r["printed"] for r in rows) > 0


def test_a_number_toc_does_not_have_is_read_as_heading_text(site, capsys):
    pages, _ = site
    pages["https://example.com/a.md"] = ("text/markdown", "# 2024\nthat year\n# 2025\nthis year\n")
    _, by_text, _ = run(capsys, "section", "https://example.com/a.md", "2024")
    status, out, err = run(capsys, "section", "https://example.com/a.md", "²")
    assert by_text == "# 2024\nthat year\n"
    assert status == 1 and out == "" and "no heading matches" in err


@pytest.mark.parametrize("error", [ConnectionResetError("reset"), http.client.IncompleteRead(b"")])
def test_a_connection_that_breaks_while_reading_fails_with_a_message(monkeypatch, error):
    def fetch(url):
        raise error

    monkeypatch.setattr(page, "fetch", fetch)
    with pytest.raises(SystemExit) as exit:
        cli.main(["toc", "https://example.com/a.md"])
    assert "cannot fetch" in str(exit.value)


def test_stats_skips_unreadable_lines_in_the_record(capsys, tmp_path, monkeypatch):
    log = tmp_path / "log.jsonl"
    monkeypatch.setenv("NIBS_LOG", str(log))
    good = json.dumps({"time": "2026-11-03T00:00:00", "cmd": "toc", "url": "u", "page": 100, "printed": 10})
    log.write_text(good + '\n{"time": "2026-11\n' + json.dumps({"time": 1}) + "\n")
    status, out, _ = run(capsys, "stats")
    assert status == 0
    assert "1 runs over 1 page-days" in out and "skipped 2 unreadable lines" in out
