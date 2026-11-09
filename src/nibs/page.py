"""Fetching a page as Markdown-like text and splitting it by its headings."""

import http.client
import re
import urllib.error
import urllib.request
from collections import Counter
from html.parser import HTMLParser

from . import __version__, cache

MAX_BYTES = 5_000_000
USER_AGENT = f"nibs/{__version__} (+https://github.com/nhinata/nibs)"
CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")
# What fetching can raise: URLError and the socket and SSL errors that reading
# the body raises are all OSError; http.client raises HTTPException subclasses
# such as IncompleteRead; a malformed URL raises ValueError.
FETCH_ERRORS = (OSError, http.client.HTTPException, ValueError)

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
    return ctype.split(";")[0].strip(), decode(ctype, body[:MAX_BYTES])


def decode(ctype, body):
    try:
        return body.decode(encoding(ctype, body), "replace")
    except (LookupError, UnicodeError):  # a charset Python does not know, or one that cannot decode text
        return body.decode("utf-8", "replace")


CHARSET = re.compile(rb"""charset\s*=\s*["']?([\w.:-]+)""", re.IGNORECASE)


def encoding(ctype, body):
    """The charset in the Content-Type header, else, for an HTML page, one a <meta> tag
    declares in the first 1,024 bytes (<meta charset> or <meta http-equiv>, as browsers
    look), else UTF-8."""
    m = CHARSET.search(ctype.encode("latin-1", "replace"))
    if m is None and looks_like_html(ctype, body[:1024].decode("latin-1")):
        m = re.search(rb"<meta[^>]*?" + CHARSET.pattern, body[:1024], re.IGNORECASE)
    return m.group(1).decode("ascii") if m else "utf-8"


def looks_like_html(ctype, text):
    return "html" in ctype or text.lstrip()[:15].lower().startswith(("<!doctype", "<html"))


class TextOfHtml(HTMLParser):
    """Headings become Markdown headings, <pre> becomes a code block, other block text becomes lines.

    Only heading tags make headings and only <pre> makes code blocks: a text line
    that sections() would read as a heading or a fence is escaped with a backslash.
    """

    NOT_SHOWN = {"script", "style", "noscript", "svg"}  # a browser shows no text from these
    SKIP = NOT_SHOWN | {"nav", "aside"}
    # The page's own header and footer (banner, site links) are left out; inside
    # <article>, <main> or <section> they belong to that content and are kept.
    PAGE_ONLY = {"header", "footer"}
    SECTIONING = {"article", "main", "section"}
    # The roles that <nav>, <aside> and the page's own <header> and <footer> have: an element
    # given one of them by its role attribute is left out too. A browser takes the first role
    # it knows from the list; only the first is looked at here.
    LEFT_OUT_ROLES = {"navigation", "complementary", "banner", "contentinfo"}
    BLOCK = {"p", "li", "td", "th", "blockquote", "dt", "dd", "div", "section", "article", "main", "tr", "br", "form"}
    # Elements with no contents, so a closing tag for one closes nothing. "<img />" reads as a start and a closing tag.
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lines, self.buf, self.heading, self.sectioning, self.pre = [], [], 0, 0, None
        self.skip = None  # the tag of the element being left out
        self.opened = Counter()  # the elements open inside it, itself included

    def flush(self):
        text = " ".join("".join(self.buf).split())
        if text:
            if self.heading:
                text = "#" * self.heading + " " + text
            elif HEADING.match(text) or FENCE.match(text):
                text = "\\" + text  # text, not a heading or a fence
            self.lines.append(text)
        self.buf = []

    def starts_left_out(self, tag, attrs):
        if self.pre is not None:  # a browser shows the text after <Header> in a code block, as in List<Header> h
            return tag in self.NOT_SHOWN
        if tag in self.SKIP or (tag in self.PAGE_ONLY and not self.sectioning):
            return True
        if tag in self.VOID:
            return False
        role = next((value for name, value in attrs if name == "role"), None)  # the first, as a browser takes
        first = (role or "").split()[:1]
        return bool(first) and first[0] in self.LEFT_OUT_ROLES

    def handle_starttag(self, tag, attrs):
        if self.skip:
            if tag not in self.VOID:
                self.opened[tag] += 1
            return
        if tag in self.PAGE_ONLY:
            self.flush()
        if self.starts_left_out(tag, attrs):
            if tag not in self.NOT_SHOWN:  # shown as a block, so the text on either side is not run together
                self.flush()
            self.skip, self.opened = tag, Counter([tag])
            return
        if self.pre is not None:
            if tag == "br":
                self.pre.append("\n")
            return
        if re.fullmatch(r"h[1-6]", tag):
            self.flush()
            self.heading = int(tag[1])
        elif tag == "pre":
            self.flush()
            self.pre = []
        elif tag in self.BLOCK:
            self.flush()
        if tag in self.SECTIONING:
            self.sectioning += 1

    def handle_endtag(self, tag):
        if self.skip:
            if self.opened[tag]:
                self.opened[tag] -= 1
                if tag != self.skip or self.opened[tag]:
                    return
            elif tag in self.VOID or tag in self.SKIP:
                return
            # Otherwise the tag closes an element around the skipped one, which ends it too.
            self.skip = None
        if self.pre is not None:
            if tag == "pre":
                self.end_pre()
            return
        if tag in self.PAGE_ONLY:
            self.flush()
        elif re.fullmatch(r"h[1-6]", tag):
            self.flush()
            self.heading = 0
        elif tag in self.BLOCK:
            self.flush()
        if tag in self.SECTIONING:
            self.sectioning = max(0, self.sectioning - 1)

    def end_pre(self):
        code = "".join(self.pre).strip("\n")
        self.pre = None
        if not code.strip():
            return
        # Longer than any run of backticks in the code, so that nothing in it closes the fence.
        fence = "`" * max(3, max((len(r) for r in re.findall(r"`+", code)), default=0) + 1)
        self.lines.append(f"{fence}\n{code}\n{fence}")

    def handle_data(self, data):
        if self.skip:
            return
        if self.pre is not None:
            self.pre.append(data)
        else:
            self.buf.append(data)


def html_to_text(html):
    parser = TextOfHtml()
    parser.feed(html)
    parser.close()
    if parser.pre is not None:  # a <pre> the page never closed
        parser.end_pre()
    parser.flush()
    return "\n\n".join(parser.lines)


def load(url):
    """(text, source): the page as Markdown-like text, from the cache when it was read
    recently, and how it was read: "md" (the URL with .md added), "html" (the URL's
    HTML turned into text) or "text" (the URL's own answer, used as it came)."""
    cached = cache.get(url)
    if cached is not None:
        return cached
    text, source = _download(url)
    cache.put(url, text, source)
    return text, source


def _download(url):
    ctype, text = fetch(url)
    if looks_like_html(ctype, text) and not url.endswith(".md"):
        # Many documentation sites serve the page's Markdown at the same URL plus .md.
        try:
            mctype, mtext = fetch(url.split("#")[0].rstrip("/") + ".md")
            if not looks_like_html(mctype, mtext) and mtext.strip():
                return CONTROL.sub("", mtext), "md"
        except FETCH_ERRORS:
            pass
    if looks_like_html(ctype, text):
        return CONTROL.sub("", html_to_text(text)), "html"
    return CONTROL.sub("", text), "text"


# The Markdown structure sections() reads (README: Headings and code blocks).
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
FENCE = re.compile(r"^(`{3,}|~{3,})(.*)$")


def sections(text):
    """(lines, [(level, title, start, end)]) over the lines of `text`.

    The Markdown nibs reads is described in README (Headings and code blocks): only
    `#` headings and code fences, by nibs' own small rule, not all of CommonMark.
    """
    lines = text.split("\n")
    heads, fence = [], None
    for i, line in enumerate(lines):
        m = FENCE.match(line.strip())
        if fence is not None:
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence) and not m.group(2).strip():
                fence = None
            continue
        if m:
            fence = m.group(1)
            continue
        h = HEADING.match(line)
        if h:
            heads.append((len(h.group(1)), h.group(2), i))
    # A section ends at the next heading of its level or above. Each heading ends
    # the open sections at its level or below; the ones still open run to the end.
    ends, open_ = [len(lines)] * len(heads), []
    for n, (level, _, start) in enumerate(heads):
        while open_ and heads[open_[-1]][0] >= level:
            ends[open_.pop()] = start
        open_.append(n)
    return lines, [(level, title, start, end) for (level, title, start), end in zip(heads, ends)]
