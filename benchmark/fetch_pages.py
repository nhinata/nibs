"""Read the pages of a benchmark set the way nibs reads them and keep every answer.

    fetch_pages.py OUT docs.txt general.txt

Each list's file name is the name of its group. OUT/pages.jsonl lists the pages.
"""

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import responses
from nibs import page


class Recording:
    """An opener that keeps what another opener answers, for page.fetch to read."""

    def __init__(self, opener, directory):
        self.opener = opener
        self.directory = directory

    def open(self, req, timeout=None):
        url = req.full_url
        try:
            with self.opener.open(req, timeout=timeout) as res:
                body = res.read(page.MAX_BYTES + 1)
                content_type = res.headers.get("Content-Type", "")
                final_url = res.geturl()
        except Exception as err:
            responses.save(self.directory, url, error=str(err))
            raise
        responses.save(self.directory, url, content_type=content_type, final_url=final_url, body=body)
        return Answer(content_type, final_url, body)


class Answer:
    """What page.fetch reads of a response."""

    def __init__(self, content_type, url, body):
        self.headers = {"Content-Type": content_type}
        self.url = url
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, size=-1):
        return self.body[:size] if size >= 0 else self.body

    def geturl(self):
        return self.url


class Saved:
    """An opener that answers only from a directory of kept answers, without a network."""

    def __init__(self, directory):
        self.directory = directory

    def open(self, req, timeout=None):
        saved = responses.load(self.directory, req.full_url)
        if saved is None:
            raise OSError("not in the benchmark set")
        meta, body = saved
        if meta["error"] is not None:
            raise OSError(meta["error"])
        return Answer(meta["content_type"], meta["final_url"], body)


def read_page(url):
    """The reason a page could not be read, or None."""
    try:
        page._download(url)
    except Exception as err:
        return str(err) or type(err).__name__
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    parser.add_argument("lists", type=Path, nargs="+")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    page._OPENER = Recording(page._OPENER, args.out)
    pages = [
        {"group": path.stem, "url": url}
        for path in args.lists
        for url in path.read_text(encoding="utf-8").split()
    ]
    with ThreadPoolExecutor(8) as pool:
        errors = pool.map(read_page, (entry["url"] for entry in pages))
        lines = [json.dumps({**entry, "error": error}) for entry, error in zip(pages, errors)]
    (args.out / "pages.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
