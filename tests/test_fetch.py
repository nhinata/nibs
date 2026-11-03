import http.server
import threading

import pytest

from nibs import cli, page


@pytest.fixture
def server():
    """A web server on localhost: /doc serves Markdown, /to?<url> redirects to <url>."""

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.startswith("/to?"):
                self.send_response(302)
                self.send_header("Location", self.path[len("/to?"):])
                self.end_headers()
                return
            body = b"# Doc\nhello\n"
            self.send_response(200)
            self.send_header("Content-Type", "text/markdown; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    httpd = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()
    httpd.server_close()


def test_a_web_page_is_read(server):
    assert page.fetch(server + "/doc") == ("text/markdown", "# Doc\nhello\n")


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
