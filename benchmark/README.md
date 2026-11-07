# Benchmark for reading HTML

A fixed set of pages for comparing two versions of nibs: what each version makes of the same answers from the same pages. It is not part of the package or of the tests, and nothing in CI depends on it.

A set is chosen once and then stays as it is. Its settings are in `v1/config.json`. To look at a newer web or at other pages, make a new set (`v2`) next to it instead of changing this one.

## The set

| Group | Pages | How they are chosen | What it stands for | What it does not stand for |
| --- | --- | --- | --- | --- |
| `docs` | the count in the config | Products of [DevDocs](https://github.com/freeCodeCamp/devdocs), by the address its scraper reads from at the pinned commit; for each product, one page in the same directory linked from that address, or the address itself if it links to none | Documentation of open-source programming tools | Other documentation (cloud vendors, internal sites), blogs, and pages that are not linked from where the documentation starts |
| `general` | the count in the config | Domains at random from the top of a [Tranco](https://tranco-list.eu) list, fixed by its ID; the top page of each | Top pages of popular sites, to see harm outside documentation | Articles and documentation on those sites |

Results of the two groups are never added together.

- A page is not replaced once chosen. A page that cannot be read stays in the set and is counted with its reason.
- Some sites answer a request from a data center differently from one from a home network, so the number of unread pages says little about other places.
- Scrapers that name no address that can be read from the web are left out; `select_pages.py` prints them.
- Only the rules and the list of `docs` pages are in this repository. The `general` list follows from the Tranco ID, the top and the seed. The answers themselves are other people's pages and are kept elsewhere.

## Running it

```sh
pip install -e .
git clone https://github.com/freeCodeCamp/devdocs
git -C devdocs checkout <devdocs_commit in the config>
python benchmark/select_pages.py docs benchmark/v1/config.json --devdocs devdocs > docs.txt
python benchmark/select_pages.py general benchmark/v1/config.json > general.txt
python benchmark/fetch_pages.py pages docs.txt general.txt
```

`fetch_pages.py` asks through nibs' own code, so it asks what nibs asks, and keeps every answer in `pages/`.

To compare two checkouts:

```sh
python benchmark/compare.py pages ../nibs-main/src ./src > report.md
```

The report has a row for each group and a diff for each page that changed, starting from the ones that lost the largest share of their text. It does not decide anything: whether the text that went away was noise or content has to be read from the diffs.

Only reading can be compared this way. A version that asks for an address that was not asked for when the set was made gets "not in the benchmark set" as its answer.
