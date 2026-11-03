import json
import time

from nibs import cache, cli

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


def test_a_fence_is_closed_only_by_one_as_long_with_nothing_after_it(site, capsys):
    pages, _ = site
    pages["https://example.com/a.md"] = ("text/markdown", "\n".join([
        "# Real",
        "````md",
        "```sh",
        "# a comment in the shown sample",
        "```",
        "# a heading in the shown sample",
        "````",
        "~~~",
        "~~~ not a closing fence: text after it",
        "# still code",
        "~~~",
        "## Also real",
    ]))
    _, out, _ = run(capsys, "toc", "https://example.com/a.md")
    assert "2 headings" in out and "Also real" in out


def test_the_page_header_is_left_out_but_an_article_header_is_kept(site, capsys):
    pages, _ = site
    pages[HTML_URL] = ("text/html", "<html><body><header><h1>Site name</h1></header><article>"
                                    "<header><h1>Post title</h1></header><p>text</p></article>"
                                    "<footer>site links</footer></body></html>")
    _, out, _ = run(capsys, "toc", HTML_URL)
    assert "Post title" in out and "Site name" not in out


def test_a_page_wrapped_in_a_form_is_read(site, capsys):
    pages, _ = site
    pages[HTML_URL] = ("text/html", '<html><body><form id="form1"><h1>Title</h1><p>body</p></form></body></html>')
    _, out, _ = run(capsys, "section", HTML_URL, "Title")
    assert out.split() == ["#", "Title", "body"]


def test_only_heading_tags_make_headings(site, capsys):
    pages, _ = site
    pages[HTML_URL] = ("text/html", "<html><body><h1>Install</h1><p>#hashtag</p>"
                                    "<pre># install deps\npip install x</pre></body></html>")
    _, toc, _ = run(capsys, "toc", HTML_URL)
    _, section, _ = run(capsys, "section", HTML_URL, "1")
    assert "1 headings" in toc
    assert "# install deps\npip install x\n" in section
