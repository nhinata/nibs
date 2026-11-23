"""Pages already read, so that toc, section and find on one page fetch it once."""

import hashlib
import json
import os
import time

from .paths import get_cache_dir

# How long a fetched page is reused; the same default as Claude Code's WebFetch.
TTL_SECONDS = 15 * 60
# What an entry keeps of a page, as page.load gives it back.
FIELDS = ("text", "source", "cut")


def _get_path(url):
    return get_cache_dir() / (hashlib.sha256(url.encode()).hexdigest() + ".json")


def get(url):
    """(text, source, cut) of a page read recently, else None."""
    try:
        with open(_get_path(url), encoding="utf-8") as f:
            entry = json.load(f)
    except (OSError, ValueError):
        return None
    if time.time() - entry.get("time", 0) > TTL_SECONDS:
        return None
    # An entry written before a field was kept is fetched again.
    if any(entry.get(field) is None for field in FIELDS):
        return None
    return tuple(entry[field] for field in FIELDS)


def put(url, text, source, cut):
    try:
        get_cache_dir().mkdir(parents=True, exist_ok=True)
        _prune()
        tmp = _get_path(url).with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            # The entry is found by the hash of its URL and does not keep the URL, which can carry a credential.
            json.dump({"time": time.time(), **dict(zip(FIELDS, (text, source, cut), strict=True))}, f)
        os.replace(tmp, _get_path(url))
    except OSError:
        pass  # A page that cannot be cached is fetched again next time.


def _prune():
    now = time.time()
    # A .tmp is left by a run stopped while writing; one still being written is newer.
    for p in [*get_cache_dir().glob("*.json"), *get_cache_dir().glob("*.tmp")]:
        try:
            if now - p.stat().st_mtime > TTL_SECONDS:
                p.unlink()
        except OSError:
            pass
