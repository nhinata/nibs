# nibs

Read a web page by its headings: list them, then print only the section you need.

An AI agent that reads a whole documentation page to answer one question puts tens of thousands of characters into its context, most of which it never uses. nibs lets it look at the page's headings first and then take just one section, in the page's own words.

```console
$ nibs toc https://www.postgresql.org/docs/current/sql-select.html
63,204 chars, 37 headings
  1.   SELECT  (69)
  2.   Synopsis  (2,525)
  3.   Description  (3,137)
  4.   Parameters  (46,642)
  5.     WITH Clause  (5,818)
  ...
 19.     The Locking Clause  (4,105)
  ...
$ nibs find https://www.postgresql.org/docs/current/sql-select.html NOWAIT --limit 2
## Synopsis
  [ FOR { UPDATE | NO KEY UPDATE | SHARE | KEY SHARE } [ OF from_reference [, ...] ] [ NOWAIT | SKIP LOCKED ] [...] ]
## The Locking Clause
  FOR lock_strength [ OF from_reference [, ...] ] [ NOWAIT | SKIP LOCKED ]
[nibs: stopped at 2 matches; pass --limit]
$ nibs section https://www.postgresql.org/docs/current/sql-select.html 19
```

## Install

```sh
pipx install nibs      # or: uv tool install nibs
```

Python 3.11 or later. No other dependencies.

## Commands

```sh
nibs toc <url>                  # headings, numbered, with each section's size in characters
nibs section <url> <n|heading>  # one section, by its number in toc or by heading text
nibs find <url> <regex>         # matching lines, each under the heading it belongs to
nibs stats                      # characters printed so far, against reading each page whole
```

- `section` prints at most 8,000 characters; `--max` changes that. A heading given as text matches exactly first, then as a case-insensitive substring.
- `find` prints at most 30 lines; `--limit` changes that.

## How a page is read

- Only `http` and `https` URLs are read, also when a page redirects.
- If the site serves Markdown, either at the URL itself or at the URL with `.md` added, nibs uses it. Many documentation sites do.
- Otherwise nibs turns the HTML into headings, text and code blocks (from `<pre>`). It leaves out scripts, styles, templates, navigation, sidebars, and the page's own header and footer; a header or footer inside an article is kept. An element whose `role` attribute gives it the role of one of these (`navigation`, `complementary`, `banner` or `contentinfo`) is left out too, even inside an article; only the first value in the attribute is looked at. A left-out element ends at its closing tag, or at the closing tag of an element around it: when a page leaves one unclosed, the text after it is kept. Text can get through the same way when a closing tag appears inside a left-out element that it does not belong to, and after an HTML element written as `<nav/>`, which ends there although a browser keeps it open. Inside `<pre>`, only scripts, styles, templates, `<noscript>` and `<svg>` are left out. A `<template>` whose `shadowrootmode` is `open` or `closed` is a shadow root that a browser shows, and is kept; only that value is looked at, not the other conditions for a shadow root, and the children of its host are kept whether a browser shows them or not. Text hidden by the `hidden` attribute or by CSS is kept. Only heading tags become headings, and only `<pre>` becomes a code block: a line of text that would read as either (see below) gets a backslash in front.
- nibs tells what an element is only from what HTML defines: its tag name and standard attributes such as `role`. It does not guess from `class`, `id` or the look of the text. So a mark that a site puts in its headings stays in the heading text, such as the `¶` that Sphinx links each heading with (`prog¶`); `section` still finds such a heading by its number or by part of its text.
- Control characters in the page are removed before printing.
- nibs does not run JavaScript. A page that builds its content in the browser comes back with little or no text; when no headings are found, nibs says so.
- A fetched page is used for 15 minutes from `~/.cache/nibs` (or `$XDG_CACHE_HOME/nibs`), so `toc`, `section` and `find` on the same page fetch it once. A later run that fetches a page removes what is older than that.

### Headings and code blocks

nibs splits a page by its Markdown headings. It reads only what it needs for that, by this rule rather than all of CommonMark:

- A heading is a line that starts with 1 to 6 `#` and a space.
- A line that starts with three or more `` ` `` or `~` opens a code block, after any spaces. The block ends at a line of the same character, at least as long, with nothing after it. Headings inside a code block are not headings.
- Nothing else is read as structure: not headings underlined with `===` or `---`, not code indented by four spaces.

## Using it from an agent

Tell the agent in its instructions, for example in `CLAUDE.md` or `AGENTS.md`:

```markdown
To read documentation on the web, run `nibs toc <url>` to see the headings,
then `nibs section <url> <n>` for the part you need, or `nibs find <url> <regex>`.
```

What nibs prints is the page's own text, including text the page hides from a person reading it. Have the agent read it as data, not as instructions.

## The usage record

Each run adds one line to `~/.local/state/nibs/usage.jsonl` (or `$XDG_STATE_HOME/nibs/usage.jsonl`): the time, the command, the URL's scheme, host, port and path (not the user name and password, the query string or the fragment, which can carry a credential), the page's size, how many characters were printed, how many headings the page has, and how it was read (`md` for the URL with `.md` added, `html` for HTML turned into text, `text` for any other answer, used as it came). `nibs stats` reads it. Set `NIBS_LOG` to another path to keep the record there. Nothing is sent anywhere.

## License

MIT
