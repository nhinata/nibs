"""Choose the pages of a benchmark set, by the rules in benchmark/README.md.

    select_pages.py docs CONFIG --devdocs DIR > docs.txt
    select_pages.py general CONFIG > general.txt
"""

import argparse
import json
import random
import re
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from pathlib import Path

from nibs import page

BASE_URL = re.compile(r"self\.base_urls?\s*=\s*(?:\[\s*|%w\[\s*|%w\(\s*)?['\"]?(http[^'\"\s,\]\)]+)")
NAME = re.compile(r"self\.name\s*=\s*['\"]([^'\"]+)")
CLASS = re.compile(r"class\s+(\w+)\s*<")
VERSION = re.compile(r"version\s+['\"]([^'\"]*)['\"]\s+do")
RELEASE = re.compile(r"self\.release\s*=\s*['\"]([^'\"]*)")
LOCAL_HOSTS = ("localhost", "127.0.0.1")


def base_url(source):
    """The first address a DevDocs scraper reads from, which is that of its newest version;
    None if the source does not name one that can be read from the web."""
    found = BASE_URL.search(source)
    if not found:
        return None
    url = found.group(1)
    before = source[: found.start()]
    for key, pattern in (("version", VERSION), ("release", RELEASE)):
        # The value set closest before the address, or else the first one set after it.
        value = (pattern.findall(before)[-1:] or pattern.findall(source)[:1] or [None])[0]
        if value is not None:
            url = re.sub(r"#\{(self\.)?" + key + r"\}", value, url)
    if "#{" in url or urllib.parse.urlsplit(url).hostname in LOCAL_HOSTS:
        return None
    return url


def products(devdocs):
    """{product name: base URL} of a DevDocs checkout, and the scrapers left out."""
    found, left_out = {}, []
    for path in sorted(Path(devdocs, "lib/docs/scrapers").rglob("*.rb")):
        source = path.read_text(encoding="utf-8", errors="replace")
        url = base_url(source)
        if url is None:
            left_out.append(path.stem)
            continue
        name = NAME.search(source) or CLASS.search(source)
        found[name.group(1) if name else path.stem] = url
    return found, left_out


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.hrefs += [value for key, value in attrs if key == "href" and value]


def links_under(url, html):
    """The pages an HTML page links to in its own directory, in a fixed order."""
    parser = Links()
    parser.feed(html)
    directory = url.rsplit("/", 1)[0] + "/"
    own = urllib.parse.urldefrag(url)[0].rstrip("/")
    links = {urllib.parse.urldefrag(urllib.parse.urljoin(url, href))[0] for href in parser.hrefs}
    return sorted(link for link in links if link.startswith(directory) and link.rstrip("/") != own)


def read_start_page(url):
    """(where the URL led, its text), the way nibs asks for an HTML page."""
    req = urllib.request.Request(url, headers={"User-Agent": page.USER_AGENT, "Accept": "text/html"})
    with page._OPENER.open(req, timeout=20) as res:
        body = res.read(page.MAX_BYTES)
        return res.geturl(), page.decode(res.headers.get("Content-Type", ""), body)


def pick_page(seed, name, url):
    """A page linked from the start page, or the start page if it cannot be read or links nowhere."""
    try:
        final, html = read_start_page(url)
        links = links_under(final, html)
    except Exception as err:  # a start page that cannot be read stays in the set, as unread
        print(f"{name}: {url}: {err}", file=sys.stderr)
        return url
    return random.Random(f"{seed}:{name}").choice(links) if links else final


def select_docs(config, devdocs):
    found, left_out = products(devdocs)
    print(f"{len(found)} products; left out: {', '.join(left_out)}", file=sys.stderr)
    names = random.Random(config["seed"]).sample(sorted(found), min(config["docs"]["count"], len(found)))
    with ThreadPoolExecutor(8) as pool:
        return list(pool.map(lambda name: pick_page(config["seed"], name, found[name]), names))


def select_general(config):
    settings = config["general"]
    url = f"https://tranco-list.eu/download/{settings['tranco_list']}/{settings['top']}"
    req = urllib.request.Request(url, headers={"User-Agent": page.USER_AGENT})
    with page._OPENER.open(req, timeout=60) as res:
        rows = res.read().decode().splitlines()
    domains = [row.split(",", 1)[1] for row in rows]
    return [f"https://{domain}/" for domain in random.Random(config["seed"]).sample(domains, settings["count"])]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("set", choices=["docs", "general"])
    parser.add_argument("config", type=Path)
    parser.add_argument("--devdocs", type=Path, help="a checkout of DevDocs at the commit in the config")
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    if args.set == "docs":
        if not args.devdocs:
            parser.error("docs needs --devdocs")
        urls = select_docs(config, args.devdocs)
    else:
        urls = select_general(config)
    print("\n".join(urls))


if __name__ == "__main__":
    main()
