"""Fetching a page as Markdown-like text and splitting it by its headings."""

import re
import urllib.error
import urllib.request
from html.parser import HTMLParser

from . import __version__, cache

MAX_BYTES = 5_000_000
USER_AGENT = f"nibs/{__version__} (+https://github.com/nhinata/nibs)"
CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")
FETCH_ERRORS = (urllib.error.URLError, ValueError, TimeoutError)

# Web pages only: an opener with no handlers for file:, ftp: or data: URLs, so
# that neither a URL given to nibs nor a redirect can read anything else.
# ProxyHandler adds a handler for every scheme it has a proxy for (ftp_proxy
# would make ftp: URLs go through the proxy), so it gets the web ones only.
_WEB = ("http", "https")
_OPENER = urllib.request.OpenerDirector()
for _handler in (
    urllib.request.ProxyHandler({k: v for k, v in urllib.request.getproxies().items() if k.lower() in _WEB}),
    urllib.request.UnknownHandler(),
    urllib.request.HTTPHandler(),
    urllib.request.HTTPSHandler(),
    urllib.request.HTTPDefaultErrorHandler(),
    urllib.request.HTTPRedirectHandler(),
    urllib.request.HTTPErrorProcessor(),
):
    _OPENER.add_handler(_handler)


def fetch(url):
    """(content type, text) of the response."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "text/markdown, text/html;q=0.9, */*;q=0.5"},
    )
    with _OPENER.open(req, timeout=20) as res:
        body = res.read(MAX_BYTES + 1)
        ctype = res.headers.get("Content-Type", "")
    charset = re.search(r"charset=([\w-]+)", ctype)
    try:
        text = body[:MAX_BYTES].decode(charset.group(1) if charset else "utf-8", "replace")
    except LookupError:  # a charset Python does not know
        text = body[:MAX_BYTES].decode("utf-8", "replace")
    return ctype.split(";")[0].strip(), text


def looks_like_html(ctype, text):
    return "html" in ctype or text.lstrip()[:15].lower().startswith(("<!doctype", "<html"))


class TextOfHtml(HTMLParser):
    """Headings become Markdown headings; block text becomes lines."""

    SKIP = {"script", "style", "nav", "header", "footer", "aside", "noscript", "svg", "form"}
    BLOCK = {"p", "li", "pre", "td", "th", "blockquote", "dt", "dd", "div", "section", "article", "tr", "br"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lines, self.buf, self.skip, self.heading = [], [], 0, 0

    def flush(self):
        text = " ".join("".join(self.buf).split())
        if text:
            self.lines.append(("#" * self.heading + " " if self.heading else "") + text)
        self.buf = []

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip += 1
        elif re.fullmatch(r"h[1-6]", tag):
            self.flush()
            self.heading = int(tag[1])
        elif tag in self.BLOCK:
            self.flush()

    def handle_endtag(self, tag):
        if tag in self.SKIP:
            self.skip = max(0, self.skip - 1)
        elif re.fullmatch(r"h[1-6]", tag):
            self.flush()
            self.heading = 0
        elif tag in self.BLOCK:
            self.flush()

    def handle_data(self, data):
        if not self.skip:
            self.buf.append(data)


def html_to_text(html):
    parser = TextOfHtml()
    parser.feed(html)
    parser.close()
    parser.flush()
    return "\n\n".join(parser.lines)


def load(url):
    """The page as Markdown-like text, from the cache when it was read recently."""
    text = cache.get(url)
    if text is None:
        text = _download(url)
        cache.put(url, text)
    return text


def _download(url):
    ctype, text = fetch(url)
    if looks_like_html(ctype, text) and not url.endswith(".md"):
        # Many documentation sites serve the page's Markdown at the same URL plus .md.
        try:
            mctype, mtext = fetch(url.split("#")[0].rstrip("/") + ".md")
            if not looks_like_html(mctype, mtext) and mtext.strip():
                return CONTROL.sub("", mtext)
        except FETCH_ERRORS:
            pass
    if looks_like_html(ctype, text):
        text = html_to_text(text)
    return CONTROL.sub("", text)


def sections(text):
    """(lines, [(level, title, start, end)]) over the lines of `text`, ignoring code fences."""
    lines = text.split("\n")
    heads, fence = [], None
    for i, line in enumerate(lines):
        m = re.match(r"^(`{3,}|~{3,})", line.strip())
        if m:
            if fence is None:
                fence = m.group(1)[0]
            elif fence == m.group(1)[0]:
                fence = None
            continue
        if fence:
            continue
        h = re.match(r"^(#{1,6})\s+(.*?)\s*#*\s*$", line)
        if h:
            heads.append((len(h.group(1)), h.group(2), i))
    out = []
    for n, (level, title, start) in enumerate(heads):
        end = next((s for lv, _, s in heads[n + 1:] if lv <= level), len(lines))
        out.append((level, title, start, end))
    return lines, out
