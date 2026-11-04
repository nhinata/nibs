"""nibs: read only the part of a web page you need.

  nibs toc <url>                 headings with their numbers and sizes
  nibs section <url> <n|text>    one section (number from toc, or heading text)
  nibs find <url> <regex>        matching lines, each with the section it is in
  nibs stats                     how much of the pages nibs has printed so far

Pages are fetched as Markdown when the site serves it (the URL itself, or the
URL with .md added); otherwise the HTML is turned into headings and text.
A page is fetched once and reused for 15 minutes.
"""

import argparse
import contextlib
import io
import re
import sys

from . import __version__, page, usage

NO_HEADINGS = (
    "[nibs: no headings found. If the page shows more in a browser, it is likely "
    "drawn by JavaScript, which nibs does not run]"
)


def cmd_toc(text, lines, secs, _args):
    print(f"{len(text):,} chars, {len(secs)} headings")
    for n, (level, title, start, end) in enumerate(secs, 1):
        size = sum(len(line) + 1 for line in lines[start:end])
        print(f'{n:3}. {"  " * (level - 1)}{title}  ({size:,})')
    if not secs:
        print(NO_HEADINGS)


def cmd_section(_text, lines, secs, args):
    if not secs:
        print(NO_HEADINGS, file=sys.stderr)
        return 1
    # A number picks the section with that number in toc; anything else, or a
    # number toc does not have (a heading such as "2024"), is heading text.
    q = args.query
    try:
        n = int(q) if q.isascii() and q.isdigit() else 0
    except ValueError:  # more digits than int() converts
        n = 0
    if 0 < n <= len(secs):
        picked = [secs[n - 1]]
    else:
        q = q.lower()
        picked = [s for s in secs if s[1].lower() == q] or [s for s in secs if q in s[1].lower()]
    if not picked:
        print(f"nibs: no heading matches {args.query!r}; see nibs toc", file=sys.stderr)
        return 1
    if len(picked) > 1:
        print(f"{len(picked)} headings match; showing the first. Others: " + "; ".join(s[1] for s in picked[1:6]))
    _, _, start, end = picked[0]
    body = "\n".join(lines[start:end]).strip()
    if len(body) > args.max:
        print(body[: args.max])
        print(f"\n[nibs: cut at {args.max:,} of {len(body):,} chars; pick a subsection from nibs toc, or pass --max]")
    else:
        print(body)
    return 0


def cmd_find(_text, lines, secs, args):
    pattern = re.compile(args.regex, re.IGNORECASE)
    shown, last = 0, None
    for i, line in enumerate(lines):
        if not pattern.search(line):
            continue
        sec = next((s for s in reversed(secs) if s[2] <= i), None)
        if sec is not last:
            print(f'## {sec[1] if sec else "(before the first heading)"}')
            last = sec
        print(f"  {line.strip()[:300]}")
        shown += 1
        if shown >= args.limit:
            print(f"[nibs: stopped at {args.limit} matches; pass --limit]")
            break
    if not shown:
        print("no match")


def parser():
    ap = argparse.ArgumentParser(prog="nibs", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", action="version", version=f"nibs {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("toc", help="list the headings")
    p.add_argument("url")
    p = sub.add_parser("section", help="print one section")
    p.add_argument("url")
    p.add_argument("query", help="a number from toc, or heading text")
    p.add_argument("--max", type=int, default=8000, help="most characters to print (default 8000)")
    p = sub.add_parser("find", help="print matching lines with their sections")
    p.add_argument("url")
    p.add_argument("regex")
    p.add_argument("--limit", type=int, default=30, help="most lines to print (default 30)")
    sub.add_parser("stats", help="how much nibs has saved so far")
    return ap


def main(argv=None):
    args = parser().parse_args(argv)
    if args.cmd == "stats":
        return usage.print_stats()
    if args.cmd == "find":
        try:
            re.compile(args.regex)
        except re.error as err:
            sys.exit(f"nibs: bad regex {args.regex!r}: {err}")
    try:
        text, source = page.load(args.url)
    except page.FETCH_ERRORS as err:
        sys.exit(f"nibs: cannot fetch {args.url}: {err}")
    lines, secs = page.sections(text)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        status = {"toc": cmd_toc, "section": cmd_section, "find": cmd_find}[args.cmd](text, lines, secs, args)
    sys.stdout.write(out.getvalue())
    usage.record(args.cmd, args.url, len(text), len(out.getvalue()), len(secs), source)
    return status or 0
