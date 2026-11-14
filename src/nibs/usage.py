"""A local record of what nibs printed, to compare with reading whole pages.

One JSON line per run: the command, the part of the URL that is kept (see
_page_url), the page's size and how much was printed, how many headings the page
has and how it was read (see page.load). The last two show how often a page read
from HTML has no headings, as one drawn by JavaScript does. Nothing is sent anywhere.
"""

import json
import time
import urllib.parse

from .paths import usage_log


def _page_url(url):
    """The part of the URL the record keeps (README: The usage record)."""
    try:
        parts = urllib.parse.urlsplit(url)
    except ValueError:  # such as an unclosed [ in the host
        return "-"
    if parts.scheme not in ("http", "https") or not parts.netloc:
        return "-"  # a form urllib also takes, such as <URL:http://...>
    return f"{parts.scheme}://{parts.netloc.rpartition('@')[2]}{parts.path}"


def record(cmd, url, page_chars, printed_chars, headings, source):
    path = usage_log()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"time": time.strftime("%Y-%m-%dT%H:%M:%S"), "cmd": cmd, "url": _page_url(url),
                                "page": page_chars, "printed": printed_chars, "headings": headings,
                                "source": source}) + "\n")
    except OSError:
        pass  # Measuring must never stop the lookup.


def print_stats():
    rows, unreadable = [], 0
    try:
        with open(usage_log(), "rb") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    row = json.loads(line.decode("utf-8"))
                    rows.append({"time": str(row["time"]), "url": str(row["url"]),
                                 "page": int(row["page"]), "printed": int(row["printed"])})
                except (ValueError, TypeError, KeyError, OverflowError):
                    unreadable += 1  # a line cut short by a full disk or a killed run
    except FileNotFoundError:
        pass
    # Without nibs, each page would have been read whole, about once a day.
    pages = {(r["time"][:10], r["url"]): r["page"] for r in rows}
    whole = sum(pages.values())
    printed = sum(r["printed"] for r in rows)
    print(f"{len(rows)} runs over {len(pages)} page-days")
    if unreadable:
        print(f"skipped {unreadable} unreadable lines in {usage_log()}")
    if whole:
        print(f"printed {printed:,} chars; reading each page whole once a day: {whole:,} ({printed / whole:.0%} of that)")
    return 0
