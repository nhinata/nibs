# nibs

[![PyPI](https://img.shields.io/pypi/v/nibs)](https://pypi.org/project/nibs/)
[![Python](https://img.shields.io/python/required-version-toml?tomlFilePath=https://raw.githubusercontent.com/nhinata/nibs/main/pyproject.toml)](https://github.com/nhinata/nibs/blob/main/pyproject.toml)
[![Test](https://github.com/nhinata/nibs/actions/workflows/test.yml/badge.svg)](https://github.com/nhinata/nibs/actions/workflows/test.yml)

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
### The Locking Clause

FOR UPDATE, FOR NO KEY UPDATE, FOR SHARE and FOR KEY SHARE are locking clauses; they affect how SELECT locks rows as they are obtained from the table.
...
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
- For an HTML page, nibs uses the Markdown that the site serves at the URL with `.md` added to its path, if there is one.
- Otherwise nibs turns the HTML into headings, text and code blocks (from `<pre>`), leaving out scripts, styles, navigation, sidebars, and the page's own header and footer.
- nibs does not run JavaScript. A page that builds its content in the browser comes back with little or no text; when no headings are found, nibs says so.
- A fetched page is used for 15 minutes from `~/.cache/nibs` (or `$XDG_CACHE_HOME/nibs`), so `toc`, `section` and `find` on the same page fetch it once. A later run that fetches a page removes what is older than that.

The details, including where the HTML rules let text through, are in [docs/reading.md](https://github.com/nhinata/nibs/blob/main/docs/reading.md).

## Using it from an agent

In Claude Code, install the nibs plugin. It gives the agent a skill that tells it how to read a page with nibs.

```sh
claude plugin install nibs --marketplace nhinata/nibs   # Claude Code 2.1.292 or later
claude plugin update nibs@nibs                          # to update it
```

Claude Code updates the plugin on its own only when auto-update is turned on for the `nibs` marketplace in `/plugin`.

For another agent, put [the skill](https://github.com/nhinata/nibs/blob/main/plugin/skills/nibs/SKILL.md) where the agent looks for skills, or copy its text into the agent's instructions, for example in `AGENTS.md`.

What nibs prints is the page's own text, including text the page hides from a person reading it. Have the agent read it as data, not as instructions.

The skill does not let nibs run without asking. nibs fetches any URL it is given, so if you let it run without asking, text on a page could lead the agent to put data into a URL and send it to another site.

## The usage record

Each run adds one line to `~/.local/state/nibs/usage.jsonl` (or `$XDG_STATE_HOME/nibs/usage.jsonl`) with:

- the time and the command
- the URL's scheme, host, port and path (not the user name and password, the query string or the fragment, which can carry a credential)
- the page's size, how many characters were printed, and how many headings the page has
- how the page was read: `md` for the URL with `.md` added to its path, `html` for HTML turned into text, `text` for any other answer, used as it came

`nibs stats` reads it. Set `NIBS_LOG` to another path to keep the record there. Nothing is sent anywhere.

## License

MIT
