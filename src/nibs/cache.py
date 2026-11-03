"""Pages already read, so that toc, section and find on one page fetch it once."""

import hashlib
import json
import os
import time

from .paths import cache_dir

# How long a fetched page is reused; the same default as Claude Code's WebFetch.
TTL_SECONDS = 15 * 60


def _path(url):
    return cache_dir() / (hashlib.sha256(url.encode()).hexdigest() + ".json")


def get(url):
    try:
        with open(_path(url), encoding="utf-8") as f:
            entry = json.load(f)
    except (OSError, ValueError):
        return None
    if entry.get("url") != url or time.time() - entry.get("time", 0) > TTL_SECONDS:
        return None
    return entry.get("text")


def put(url, text):
    try:
        cache_dir().mkdir(parents=True, exist_ok=True)
        _prune()
        tmp = _path(url).with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"url": url, "time": time.time(), "text": text}, f)
        os.replace(tmp, _path(url))
    except OSError:
        pass  # A page that cannot be cached is fetched again next time.


def _prune():
    now = time.time()
    for p in cache_dir().glob("*.json"):
        try:
            if now - p.stat().st_mtime > TTL_SECONDS:
                p.unlink()
        except OSError:
            pass
