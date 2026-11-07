"""The answers a set of pages gave, kept in a directory: one file for what came with an
answer and one for its body, named after the URL that was asked for."""

import hashlib
import json
from pathlib import Path


def _stem(directory, url):
    return Path(directory) / "responses" / hashlib.sha256(url.encode()).hexdigest()[:32]


def save(directory, url, *, content_type=None, final_url=None, body=None, error=None):
    stem = _stem(directory, url)
    stem.parent.mkdir(parents=True, exist_ok=True)
    meta = {"url": url, "content_type": content_type, "final_url": final_url, "error": error}
    stem.with_suffix(".json").write_text(json.dumps(meta), encoding="utf-8")
    if body is not None:
        stem.with_suffix(".body").write_bytes(body)


def load(directory, url):
    """(meta, body) of what was saved for the URL, or None if it was never asked for."""
    stem = _stem(directory, url)
    try:
        meta = json.loads(stem.with_suffix(".json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    body = stem.with_suffix(".body")
    return meta, body.read_bytes() if body.exists() else None
