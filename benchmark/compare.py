"""Compare how two versions of nibs read the kept answers of a benchmark set.

    compare.py PAGES BASE_SRC HEAD_SRC > report.md

BASE_SRC and HEAD_SRC are the src directories of two checkouts. Nothing is fetched.
"""

import argparse
import collections
import difflib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve()
DIFF_LINES = 200


def read_all(pages_dir, out):
    """Read every page with the nibs on sys.path and write what came out to a file."""
    from fetch_pages import Saved
    from nibs import page

    page._OPENER = Saved(pages_dir)
    results = {}
    for line in (Path(pages_dir) / "pages.jsonl").read_text(encoding="utf-8").splitlines():
        url = json.loads(line)["url"]
        try:
            text, source = page._download(url)
        except Exception as err:
            results[url] = {"error": str(err) or type(err).__name__}
            continue
        results[url] = {"text": text, "source": source, "headings": page_headings(page, text)}
    Path(out).write_text(json.dumps(results), encoding="utf-8")


def page_headings(page, text):
    _, heads = page.sections(text)
    return [title for _, title, _, _ in heads]


def run_version(pages_dir, src, out):
    env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(Path(src).resolve()), str(HERE.parent)])}
    code = f"import compare; compare.read_all({str(pages_dir)!r}, {str(out)!r})"
    subprocess.run([sys.executable, "-c", code], check=True, env=env)
    return json.loads(Path(out).read_text(encoding="utf-8"))


def change(before, after):
    if not before:
        return 0.0 if not after else float("inf")
    return (after - before) / before


def report(pages, base, head):
    """The report as Markdown: one row per group, then the pages that changed, the ones
    that lost the largest share of their text first."""
    rows, changed = [], []
    for group, entries in _by_group(pages).items():
        counts = collections.Counter()
        sources = collections.Counter()
        chars = [0, 0]
        for entry in entries:
            url = entry["url"]
            old, new = base[url], head[url]
            if "error" in new:
                counts["unread"] += 1
                if "error" not in old:
                    counts["changed"] += 1
                    changed.append((-1.0, group, url, old, new))
                continue
            sources[new["source"]] += 1
            if "error" in old:
                counts["changed"] += 1
                changed.append((float("inf"), group, url, old, new))
                continue
            chars[0] += len(old["text"])
            chars[1] += len(new["text"])
            if old["text"] != new["text"]:
                counts["changed"] += 1
                changed.append((change(len(old["text"]), len(new["text"])), group, url, old, new))
            if set(new["headings"]) - set(old["headings"]):
                counts["headings added"] += 1
            if set(old["headings"]) - set(new["headings"]):
                counts["headings removed"] += 1
        read_as = ", ".join(f"{name} {count}" for name, count in sorted(sources.items()))
        rows.append(
            f"| {group} | {len(entries)} | {counts['unread']} | {read_as} | {counts['changed']} "
            f"| {change(*chars):+.1%} | {counts['headings added']} | {counts['headings removed']} |"
        )
    lines = [
        "| Group | Pages | Unread | Read as | Changed | Characters | Pages with headings added "
        "| Pages with headings removed |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
        *rows,
        "",
        "Unread by reason:",
        "",
    ]
    reasons = collections.Counter(head[entry["url"]]["error"] for entry in pages if "error" in head[entry["url"]])
    lines += [f"- {count}: {reason}" for reason, count in reasons.most_common()] or ["- none"]
    for share, group, url, old, new in sorted(changed, key=lambda item: item[0]):
        lines += ["", f"## {group}: {url} ({share:+.1%})", "", "````diff", *_diff(old, new), "````"]
    return "\n".join(lines) + "\n"


def _by_group(pages):
    groups = {}
    for entry in pages:
        groups.setdefault(entry["group"], []).append(entry)
    return groups


def _diff(old, new):
    lines = list(
        difflib.unified_diff(
            old.get("text", "").splitlines(), new.get("text", "").splitlines(), "base", "head", lineterm="", n=1
        )
    )
    return lines[:DIFF_LINES] + ([f"[{len(lines) - DIFF_LINES} more lines]"] if len(lines) > DIFF_LINES else [])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pages", type=Path)
    parser.add_argument("base_src", type=Path)
    parser.add_argument("head_src", type=Path)
    args = parser.parse_args()
    pages = [json.loads(line) for line in (args.pages / "pages.jsonl").read_text(encoding="utf-8").splitlines()]
    with tempfile.TemporaryDirectory() as tmp:
        base = run_version(args.pages, args.base_src, Path(tmp) / "base.json")
        head = run_version(args.pages, args.head_src, Path(tmp) / "head.json")
    sys.stdout.write(report(pages, base, head))


if __name__ == "__main__":
    main()
