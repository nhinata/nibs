"""A local record of what nibs printed, to compare with reading whole pages.

One JSON line per run: the command, the part of the URL that is kept (see
_strip_url), the page's size and how much was printed, how many headings the page
has and how it was read (see page.load). The last two show how often a page read
from HTML has no headings, as one drawn by JavaScript does. Nothing is sent anywhere.
read_runs gives the runs back for nibs stats.
"""

import json
import time
import urllib.parse

from .paths import get_usage_log


def _strip_url(url):
    """The part of the URL the record keeps (README: The usage record)."""
    try:
        parts = urllib.parse.urlsplit(url)
    except ValueError:  # such as an unclosed [ in the host
        return "-"
    if parts.scheme not in ("http", "https") or not parts.netloc:
        return "-"  # a form urllib also takes, such as <URL:http://...>
    return f"{parts.scheme}://{parts.netloc.rpartition('@')[2]}{parts.path}"


def record(cmd, url, page_chars, printed_chars, headings, source):
    path = get_usage_log()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"time": time.strftime("%Y-%m-%dT%H:%M:%S"), "cmd": cmd, "url": _strip_url(url),
                                "page": page_chars, "printed": printed_chars, "headings": headings,
                                "source": source}) + "\n")
    except OSError:
        pass  # Measuring must never stop the lookup.


def read_runs():
    """([(date, url, page size, characters printed)], how many lines could not be read),
    one tuple for each run in the record."""
    runs, unreadable = [], 0
    try:
        with open(get_usage_log(), "rb") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    row = json.loads(line.decode("utf-8"))
                    runs.append((str(row["time"])[:10], str(row["url"]), int(row["page"]), int(row["printed"])))
                except (ValueError, TypeError, KeyError, OverflowError):
                    unreadable += 1  # a line cut short by a full disk or a killed run
    except FileNotFoundError:
        pass
    return runs, unreadable
