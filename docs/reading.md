# How a page is read: the details

These are the details behind [How a page is read](../README.md#how-a-page-is-read) in the README.

## Markdown from the site

The URL with `.md` added to its path keeps the query: `/guide?lang=ja` becomes `/guide.md?lang=ja`. The answer there is used only when it comes as Markdown or plain text. The top of a site and a path that already ends in `.md` get no `.md` added.

## HTML

- A header or footer inside an article is kept.
- An element whose `role` attribute gives it the role of one of the left-out elements (`navigation`, `complementary`, `banner` or `contentinfo`) is left out too, even inside an article; only the first value in the attribute is looked at.
- A left-out element ends at its closing tag, or at the closing tag of an element around it: when a page leaves one unclosed, the text after it is kept. Text can get through the same way when a closing tag appears inside a left-out element that it does not belong to, and after an HTML element written as `<nav/>`, which ends there although a browser keeps it open.
- Inside `<pre>`, only scripts, styles, templates, `<noscript>` and `<svg>` are left out.
- A `<template>` whose `shadowrootmode` is `open` or `closed` is a shadow root that a browser shows, and is kept; only that value is looked at, not the other conditions for a shadow root, and the children of its host are kept whether a browser shows them or not.
- Text hidden by the `hidden` attribute or by CSS is kept.
- Only heading tags become headings, and only `<pre>` becomes a code block: a line of text that would read as either (see [Headings and code blocks](#headings-and-code-blocks)) gets a backslash in front.
- nibs tells what an element is only from what HTML defines: its tag name and standard attributes such as `role`. It does not guess from `class`, `id` or the look of the text. So a mark that a site puts in its headings stays in the heading text, such as the `¶` that Sphinx links each heading with (`prog¶`); `section` still finds such a heading by its number or by part of its text.

## Control characters

Control characters in the page are removed before printing.

## Headings and code blocks

nibs splits a page by its Markdown headings. It reads only what it needs for that, by this rule rather than all of CommonMark:

- A heading is a line that starts with 1 to 6 `#` and a space.
- A line that starts with three or more `` ` `` or `~` opens a code block, after any spaces. The block ends at a line of the same character, at least as long, with nothing after it. Headings inside a code block are not headings.
- Nothing else is read as structure: not headings underlined with `===` or `---`, not code indented by four spaces.
