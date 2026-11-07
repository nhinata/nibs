"""Compare how two versions of nibs read the kept answers of a benchmark set.

    compare.py PAGES BASE_SRC HEAD_SRC > report.md

BASE_SRC and HEAD_SRC are the src directories of two checkouts. Nothing is fetched.
"""

import argparse
import collections
import difflib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve()
DIFF_LINES = 200


def read_all(pages_dir, src, out):
    """Read every page with the nibs in `src` and write what came out to a file."""
    from fetch_pages import Saved
    from nibs import page

    if Path(page.__file__).resolve() != Path(src).resolve() / "nibs" / "page.py":
        raise SystemExit(f"{src}: nibs came from {page.__file__}; give the src directory of a checkout")
    page._OPENER = Saved(pages_dir)
    results = {}
    for line in (Path(pages_dir) / "pages.jsonl").read_text(encoding="utf-8").splitlines():
        url = json.loads(line)["url"]
        try:
            text, source = page._download(url)
            _, heads = page.sections(text)
        except Exception as err:
            results[url] = {"error": str(err) or type(err).__name__}
            continue
        # The length of a section, not its position: a change above it would move them all.
        sections = [[level, title, end - start] for level, title, start, end in heads]
        results[url] = {"source": source, "text": text, "sections": sections}
    Path(out).write_text(json.dumps(results), encoding="utf-8")


def run_version(pages_dir, src, out):
    env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(Path(src).resolve()), str(HERE.parent)])}
    code = f"import compare; compare.read_all({str(pages_dir)!r}, {str(src)!r}, {str(out)!r})"
    # -P: the working directory must not come before the checkout on the import path.
    run = subprocess.run([sys.executable, "-P", "-c", code], env=env)
    if run.returncode:
        raise SystemExit(run.returncode)
    return json.loads(Path(out).read_text(encoding="utf-8"))


def change(before, after):
    if not before:
        return 0.0 if not after else float("inf")
    return (after - before) / before


def report(pages, base, head):
    """The report as Markdown: one row per group, then the pages that changed, the ones
    that lost the largest share of their text first."""
    rows, changed, reasons = [], [], {}
    for group, entries in _by_group(pages).items():
        counts = collections.Counter()
        sources = collections.Counter()
        chars = [0, 0]
        reasons[group] = collections.Counter()
        for entry in entries:
            url = entry["url"]
            old, new = base[url], head[url]
            before, after = len(old.get("text", "")), len(new.get("text", ""))
            chars[0] += before
            chars[1] += after
            if "error" in new:
                counts["unread"] += 1
                reasons[group][new["error"]] += 1
            else:
                sources[new["source"]] += 1
            if old != new:
                counts["changed"] += 1
                changed.append((change(before, after), group, url, old, new))
            old_heads = collections.Counter(title for _, title, _ in old.get("sections", []))
            new_heads = collections.Counter(title for _, title, _ in new.get("sections", []))
            if new_heads - old_heads:
                counts["headings added"] += 1
            if old_heads - new_heads:
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
    ]
    for group, counter in reasons.items():
        lines += ["", f"Unread in {group}:", ""]
        lines += [f"- {count}: {reason}" for reason, count in counter.most_common()] or ["- none"]
    for share, group, url, old, new in sorted(changed, key=lambda item: item[0]):
        diff = _diff(old, new)
        longest = max(map(len, re.findall(r"`+", "\n".join(diff))), default=0)
        fence = "`" * max(4, longest + 1)
        lines += ["", f"## {group}: {url} ({share:+.1%})", "", f"{fence}diff", *diff, fence]
    return "\n".join(lines) + "\n"


def _by_group(pages):
    groups = {}
    for entry in pages:
        groups.setdefault(entry["group"], []).append(entry)
    return groups


def _fields(result):
    """What a version made of a page, as lines to compare, for each thing it made."""
    return {
        "error": [result["error"]] if "error" in result else [],
        "source": [result["source"]] if "source" in result else [],
        "text": result.get("text", "").splitlines(),
        "sections": [f"{'#' * level} {title} ({size} lines)" for level, title, size in result.get("sections", [])],
    }


def _diff(old, new):
    lines = []
    before, after = _fields(old), _fields(new)
    for field in before:
        lines += difflib.unified_diff(
            before[field], after[field], f"base {field}", f"head {field}", lineterm="", n=1
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
