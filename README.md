# nibs

Read a web page by its headings: list them, then print only the section you need.

An AI agent that reads a whole documentation page to answer one question puts tens of thousands of characters into its context, most of which it never uses. nibs lets it look at the page's headings first and then take just one section, in the page's own words.

```console
$ nibs toc https://docs.python.org/3/library/argparse.html
82,019 chars, 57 headings
  1.     Navigation  (254)
  2. argparse — Parser for command-line options, arguments and subcommands¶  (81,665)
  3.   ArgumentParser objects¶  (19,217)
  4.     prog¶  (1,483)
  5.     usage¶  (893)
  ...
$ nibs find https://docs.python.org/3/library/argparse.html allow_abbrev --limit 2
## ArgumentParser objects¶
  class argparse.ArgumentParser(prog=None, usage=None, description=None, epilog=None, ...
  allow_abbrev - Allows long options to be abbreviated if the abbreviation is unambiguous (default: True)
[nibs: stopped at 2 matches; pass --limit]
$ nibs section https://docs.python.org/3/library/argparse.html 4
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
- Otherwise nibs turns the HTML into headings, text and code blocks (from `<pre>`). It leaves out scripts, styles, navigation, sidebars, and the page's own header and footer; a header or footer inside an article is kept. Only heading tags become headings, and only `<pre>` becomes a code block: a line of text that would read as either (see below) gets a backslash in front.
- Control characters in the page are removed before printing.
- nibs does not run JavaScript. A page that builds its content in the browser comes back with little or no text; when no headings are found, nibs says so.
- A fetched page is kept for 15 minutes in `~/.cache/nibs` (or `$XDG_CACHE_HOME/nibs`), so `toc`, `section` and `find` on the same page fetch it once.

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

## The usage record

Each run adds one line to `~/.local/state/nibs/usage.jsonl` (or `$XDG_STATE_HOME/nibs/usage.jsonl`): the time, the command, the URL, the page's size, how many characters were printed, how many headings the page has, and how it was read (`md` for the URL with `.md` added, `html` for HTML turned into text, `text` for any other answer, used as it came). `nibs stats` reads it. Set `NIBS_LOG` to another path to keep the record there. Nothing is sent anywhere.

## License

MIT
