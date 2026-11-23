import http.server
import importlib
import threading

import pytest

from nibs import cli, page


@pytest.fixture
def server(monkeypatch):
    """A web server on localhost: /doc serves Markdown, /upper serves it with its type in
    capitals, /to?<url> redirects to <url>, /bytes?<n> serves n bytes of text in pieces."""

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.startswith("/to?"):
                self.send_response(302)
                self.send_header("Location", self.path[len("/to?"):])
                self.end_headers()
                return
            if self.path.startswith("/bytes?"):
                size = int(self.path[len("/bytes?"):])
                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.send_header("Content-Length", str(size))
                self.end_headers()
                try:
                    for start in range(0, size, 7):
                        self.wfile.write(b"x" * min(7, size - start))
                        self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    pass  # nibs stops reading after MAX_BYTES + 1
                return
            body = b"# Doc\nhello\n"
            self.send_response(200)
            ctype = "Text/Markdown" if self.path == "/upper" else "text/markdown; charset=utf-8"
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    # Requests to the test server must not go to a proxy set in the environment.
    monkeypatch.setenv("no_proxy", "127.0.0.1")
    httpd = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()
    httpd.server_close()


def test_a_web_page_is_read(server):
    assert page.fetch(server + "/doc") == ("text/markdown", "# Doc\nhello\n", False)


@pytest.mark.parametrize("size, cut", [(100, False), (101, True), (150, True)])
def test_a_body_over_the_limit_is_cut_and_said_to_be(server, monkeypatch, size, cut):
    monkeypatch.setattr(page, "MAX_BYTES", 100)
    assert page.fetch(f"{server}/bytes?{size}") == ("text/plain", "x" * min(size, 100), cut)


def test_a_media_type_is_read_in_any_case(server):
    assert page.fetch(server + "/upper")[0] == "text/markdown"


def test_an_ftp_proxy_does_not_open_ftp_urls(monkeypatch):
    monkeypatch.setenv("ftp_proxy", "http://127.0.0.1:9")
    importlib.reload(page)
    try:
        with pytest.raises(page.FETCH_ERRORS, match="unknown url type"):
            page.fetch("ftp://example.com/file")
    finally:
        monkeypatch.delenv("ftp_proxy")
        importlib.reload(page)


@pytest.mark.parametrize("scheme", ["file", "data"])
def test_only_web_pages_are_read_even_through_a_redirect(server, tmp_path, scheme):
    secret = tmp_path / "secret.md"
    secret.write_text("# Secret\n")
    target = {"file": secret.as_uri(), "data": "data:text/plain,secret"}[scheme]
    with pytest.raises(page.FETCH_ERRORS):
        page.fetch(target)
    with pytest.raises(page.FETCH_ERRORS):
        page.fetch(f"{server}/to?{target}")


def test_a_local_file_url_fails_with_a_message(tmp_path, capsys):
    secret = tmp_path / "secret.md"
    secret.write_text("# Secret\n")
    with pytest.raises(SystemExit) as exit:
        cli.main(["section", secret.as_uri(), "1"])
    assert "cannot fetch" in str(exit.value)
    assert capsys.readouterr().out == ""


def test_proxy_settings_in_upper_case_are_kept(monkeypatch):
    # The Windows registry can give the scheme as "HTTP"; ProxyHandler lowercases it.
    monkeypatch.setattr(page.urllib.request, "getproxies", lambda: {"HTTP": "http://proxy:3128", "FTP": "http://proxy:3128"})
    importlib.reload(page)
    try:
        handler = next(h for h in page._OPENER.handlers if isinstance(h, page.urllib.request.ProxyHandler))
        assert hasattr(handler, "http_open") and not hasattr(handler, "ftp_open")
    finally:
        monkeypatch.undo()
        importlib.reload(page)
