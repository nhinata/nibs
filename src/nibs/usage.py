"""A local record of what nibs printed, to compare with reading whole pages.

One JSON line per run: the command, the URL, the page's size and how much was
printed. Nothing is sent anywhere.
"""

import json
import time

from .paths import usage_log


def record(cmd, url, page_chars, printed_chars):
    path = usage_log()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"time": time.strftime("%Y-%m-%dT%H:%M:%S"), "cmd": cmd, "url": url,
                                "page": page_chars, "printed": printed_chars}) + "\n")
    except OSError:
        pass  # Measuring must never stop the lookup.


def print_stats():
    try:
        with open(usage_log(), encoding="utf-8") as f:
            rows = [json.loads(line) for line in f if line.strip()]
    except FileNotFoundError:
        rows = []
    # Without nibs, each page would have been read whole, about once a day.
    pages = {(r["time"][:10], r["url"]): r["page"] for r in rows}
    whole = sum(pages.values())
    printed = sum(r["printed"] for r in rows)
    print(f"{len(rows)} runs over {len(pages)} page-days")
    if whole:
        print(f"printed {printed:,} chars; reading each page whole once a day: {whole:,} ({printed / whole:.0%} of that)")
    return 0
