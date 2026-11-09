import http.client
import json
import random
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


def test_the_record_says_how_many_headings_the_page_has_and_how_it_was_read(site, capsys, tmp_path, monkeypatch):
    pages, _ = site
    pages["https://example.com/a.md"] = ("text/markdown", DOC)
    pages[HTML_URL] = ("text/html", "<html><body><h1>From HTML</h1><h2>Part</h2></body></html>")
    pages["https://example.com/both"] = ("text/html", "<html><body><h1>From HTML</h1></body></html>")
    pages["https://example.com/both.md"] = ("text/markdown", DOC)
    pages["https://example.com/app"] = ("text/html", '<html><body><div id="root"></div></body></html>')
    log = tmp_path / "log.jsonl"
    monkeypatch.setenv("NIBS_LOG", str(log))
    for url in ["https://example.com/a.md", HTML_URL, "https://example.com/both", "https://example.com/app"]:
        run(capsys, "toc", url)
    run(capsys, "toc", HTML_URL)  # from the cache
    rows = [json.loads(line) for line in log.read_text().splitlines()]
    assert [(r["headings"], r["source"]) for r in rows] == [
        (4, "text"), (2, "html"), (4, "md"), (0, "html"), (2, "html"),
    ]


def test_a_cache_entry_without_its_source_is_fetched_again(site, capsys):
    pages, calls = site
    pages["https://example.com/a.md"] = ("text/markdown", DOC)
    path = cache._path("https://example.com/a.md")
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"url": "https://example.com/a.md", "time": time.time(), "text": "# Old"}))
    _, out, _ = run(capsys, "toc", "https://example.com/a.md")
    assert calls == ["https://example.com/a.md"] and "4 headings" in out


def test_each_section_ends_at_the_next_heading_of_its_level_or_above():
    rng = random.Random(0)
    levels = [rng.randint(1, 6) for _ in range(500)]
    lines, secs = page.sections("\n".join(f'{"#" * lv} h{n}\ntext' for n, lv in enumerate(levels)))
    starts = [2 * n for n in range(len(levels))]
    expected = [
        next((starts[m] for m in range(n + 1, len(levels)) if levels[m] <= lv), len(lines))
        for n, lv in enumerate(levels)
    ]
    assert [s[3] for s in secs] == expected


@pytest.mark.parametrize("argv", [
    ["section", "https://example.com/a.md", "1", "--max", "0"],
    ["section", "https://example.com/a.md", "1", "--max", "-1"],
    ["find", "https://example.com/a.md", "run", "--limit", "0"],
    ["find", "https://example.com/a.md", "run", "--limit", "-1"],
])
def test_max_and_limit_below_1_are_refused_before_fetching(site, capsys, argv):
    pages, calls = site
    pages["https://example.com/a.md"] = ("text/markdown", DOC)
    with pytest.raises(SystemExit) as exit:
        cli.main(argv)
    assert exit.value.code == 2 and "must be 1 or more" in capsys.readouterr().err
    assert calls == []


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


def test_only_heading_tags_make_headings_and_only_pre_makes_code_blocks(site, capsys):
    pages, _ = site
    pages[HTML_URL] = ("text/html", "<html><body><h1>Install</h1><p>#hashtag</p><p># not a heading</p>"
                                    "<p>```first``` is inline code</p><p>~~~ and so is this</p>"
                                    "<pre># install deps\npip install x</pre><p>```second``` too</p>"
                                    "<h1>Usage</h1></body></html>")
    _, toc, _ = run(capsys, "toc", HTML_URL)
    _, section, _ = run(capsys, "section", HTML_URL, "1")
    assert "2 headings" in toc and "Usage" in toc
    assert "# install deps\npip install x\n" in section
    assert "\n#hashtag\n" in section and "\\# not a heading" in section and "\\```first```" in section


def test_text_on_either_side_of_a_kept_header_or_a_form_is_not_run_together(site, capsys):
    pages, _ = site
    pages[HTML_URL] = ("text/html", "<html><body><article><h1>Post</h1>Lead<header>By Alice</header>Article text"
                                    "<form>Search</form>after</article></body></html>")
    _, out, _ = run(capsys, "section", HTML_URL, "Post")
    assert out.split("\n\n") == ["# Post", "Lead", "By Alice", "Article text", "Search", "after\n"]


def test_a_code_block_is_fenced_longer_than_any_fence_in_it(site, capsys):
    pages, _ = site
    code = "```\n~~~\n# not a heading\n````"
    pages[HTML_URL] = ("text/html", f"<html><body><h1>Code</h1><pre>{code}</pre><h1>After</h1></body></html>")
    _, toc, _ = run(capsys, "toc", HTML_URL)
    _, section, _ = run(capsys, "section", HTML_URL, "Code")
    assert "2 headings" in toc
    assert f"`````\n{code}\n`````" in section


def test_a_number_toc_does_not_have_is_read_as_heading_text(site, capsys):
    pages, _ = site
    pages["https://example.com/a.md"] = ("text/markdown", "# 2024\nthat year\n# 2025\nthis year\n")
    _, by_text, _ = run(capsys, "section", "https://example.com/a.md", "2024")
    assert by_text == "# 2024\nthat year\n"
    for query in ["²", "9" * 5000]:
        status, out, err = run(capsys, "section", "https://example.com/a.md", query)
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
    damaged = good.replace('"url": "u"', '"url": "\xff"').encode("latin-1")  # not UTF-8
    log.write_bytes(good.encode() + b'\n{"time": "2026-11\n' + json.dumps({"time": 1}).encode() + b"\n"
                    + good.replace("100", "1e999").encode() + b"\n" + damaged + b"\n")
    status, out, _ = run(capsys, "stats")
    assert status == 0
    assert "1 runs over 1 page-days" in out and "skipped 4 unreadable lines" in out


@pytest.mark.parametrize("html, text", [
    ("<section><h1>A</h1><nav>menu</section><section><h1>B</h1><p>body</p></section>", "# A\n\n# B\n\nbody"),
    ("<h1>A</h1><div><aside>ad</div><p>main text</p>", "# A\n\nmain text"),
    ("<div><header>banner</div><h1>A</h1><p>text</p>", "# A\n\ntext"),
    ("<h1>A</h1><span><nav>menu</span><p>body</p>", "# A\n\nbody"),
])
def test_a_left_out_element_ends_with_the_element_around_it(html, text):
    assert page.html_to_text(html) == text


@pytest.mark.parametrize("html, text", [
    ("<h1>A</h1><nav><div>menu</div>more</nav><p>text</p>", "# A\n\ntext"),
    ("<h1>A</h1><nav><nav>a</nav>b</nav><p>text</p>", "# A\n\ntext"),
    ("<h1>A</h1><nav><div>unclosed</nav><p>text</p>", "# A\n\ntext"),
    ("<h1>A</h1><aside>ad1</nav>ad2</aside><p>text</p>", "# A\n\ntext"),
    ('<h1>A</h1><nav><img src="x" />menu<br/>more</nav><p>text</p>', "# A\n\ntext"),
])
def test_a_left_out_element_is_not_ended_by_its_own_contents(html, text):
    assert page.html_to_text(html) == text


@pytest.mark.parametrize("html", [
    '<div role="navigation"><h2>Navigation</h2><p>menu</p></div><h1>A</h1><p>text</p>',
    '<h1>A</h1><div role="complementary">ad</div><p>text</p>',
    '<article><div role="banner">site name</div><h1>A</h1><p>text</p></article>',
    '<h1>A</h1><p>text</p><section><div role="contentinfo">site links</div></section>',
    '<h1>A</h1><ul role="navigation main"><li>menu</li></ul><p>text</p>',
    '<h1>A</h1><div role="navigation"><div>menu</div>more</div><p>text</p>',
])
def test_an_element_with_the_role_of_a_left_out_element_is_left_out(html):
    assert page.html_to_text(html) == "# A\n\ntext"


@pytest.mark.parametrize("html, text", [
    ('<h1>A</h1><div role="main navigation">body</div>', "# A\n\nbody"),
    ('<h1>A</h1><div role="search">body</div>', "# A\n\nbody"),
    ('<h1>A</h1><p><img role="banner" src="x">body</p>', "# A\n\nbody"),
    ('<h1>A</h1><div role="main" role="navigation">body</div>', "# A\n\nbody"),
    ('<h1>A</h1><pre>a<span role="navigation">b</span></pre>', "# A\n\n```\nab\n```"),
])
def test_other_roles_are_kept(html, text):
    assert page.html_to_text(html) == text


def test_a_left_out_element_that_closes_does_not_end_the_article_around_it():
    html = '<article><section role="navigation">menu</section><header><h1>Title</h1></header><p>t</p></article>'
    assert page.html_to_text(html) == "# Title\n\nt"


@pytest.mark.parametrize("html", [
    "<h1>A</h1>a<nav>menu</nav>b",
    '<h1>A</h1>a<ul role="navigation"><li>menu</li></ul>b',
])
def test_text_on_either_side_of_a_left_out_element_is_not_run_together(html):
    assert page.html_to_text(html) == "# A\n\na\n\nb"


@pytest.mark.parametrize("html, code", [
    ("<h1>A</h1><pre>keep<script>var x = 1;</script>keep2</pre>", "keepkeep2"),
    ("<h1>A</h1><pre>a<noscript>x<br>y</noscript>b</pre>", "ab"),
    ("<h1>A</h1><pre>line<br>next<svg><title>Copy</title></svg></pre>", "line\nnext"),
])
def test_what_is_left_out_of_a_page_is_left_out_of_a_code_block(html, code):
    assert page.html_to_text(html) == f"# A\n\n```\n{code}\n```"


@pytest.mark.parametrize("html, code", [
    ("<h1>A</h1><pre>List<Header> h = get();\nreturn h;</pre>", "List h = get();\nreturn h;"),
    ("<h1>A</h1><pre>x = <Aside>y</Aside>;</pre>", "x = y;"),
])
def test_navigation_sidebars_headers_and_footers_are_not_left_out_of_a_code_block(html, code):
    assert page.html_to_text(html) == f"# A\n\n```\n{code}\n```"


def test_a_code_block_ends_with_its_pre_when_an_element_inside_is_left_open():
    assert page.html_to_text("<h1>A</h1><pre>a<svg>b</pre><p>after</p>") == "# A\n\n```\na\n```\n\nafter"
