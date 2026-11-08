# Benchmark for reading HTML

A fixed set of pages for comparing two versions of nibs: what each version makes of the same answers from the same pages. It is not part of the package, and its results decide nothing in CI. `tests/test_benchmark.py` tests the scripts, with the other tests.

A set is chosen once and then stays as it is. Its settings are in `v1/config.json`. To look at a newer web or at other pages, make a new set (`v2`) next to it instead of changing this one.

## The set

| Group | Pages | How they are chosen | What it stands for | What it does not stand for |
| --- | --- | --- | --- | --- |
| `docs` | the count in the config | Products of [DevDocs](https://github.com/freeCodeCamp/devdocs), by the address its scraper reads from at the pinned commit; for each product, one page in the same directory linked from that address, or the address itself if it links to none | Documentation of open-source programming tools | Other documentation (cloud vendors, internal sites), blogs, and pages that are not linked from where the documentation starts |
| `general` | the count in the config | Domains at random from the top of a [Tranco](https://tranco-list.eu) list, fixed by its ID; the top page of each | Top pages of popular sites, to see harm outside documentation | Articles and documentation on those sites |

Results of the two groups are never added together.

- The kind of a linked page is not checked before it is chosen, so the `docs` group can hold a file that is not a page, or the start page under another address. It stays in the set; such files show under "Read as" as `text`.
- A page is not replaced once chosen. A page that cannot be read stays in the set and is counted with its reason.
- Some sites answer a request from a data center differently from one from a home network, so the number of unread pages says little about other places.
- Scrapers that name no address that can be read from the web are left out; `select_pages.py` prints them.
- Only the rules and the list of `docs` pages (`v1/docs.txt`) are in this repository. The `general` list follows from the Tranco ID, the top and the seed. The answers themselves are other people's pages and are kept elsewhere.

## Running it

The work goes outside the checkout, so that other people's pages cannot end up in a commit.

```sh
pip install -e .
WORK=$(mktemp -d)
python benchmark/select_pages.py general benchmark/v1/config.json > "$WORK/general.txt"
python benchmark/fetch_pages.py "$WORK/pages" benchmark/v1/docs.txt "$WORK/general.txt"
```

`fetch_pages.py` asks through nibs' own code, so it asks what nibs asks, and keeps every answer in the directory it is given.

The `docs` list is read from `v1/docs.txt` rather than chosen again, because choosing reads the start pages as they are at the time: a later run can choose other pages. It was made with:

```sh
git clone https://github.com/freeCodeCamp/devdocs "$WORK/devdocs"
COMMIT=$(python -c 'import json; print(json.load(open("benchmark/v1/config.json"))["docs"]["devdocs_commit"])')
git -C "$WORK/devdocs" checkout "$COMMIT"
python benchmark/select_pages.py docs benchmark/v1/config.json --devdocs "$WORK/devdocs" > benchmark/v1/docs.txt
```

To compare two checkouts:

```sh
python benchmark/compare.py "$WORK/pages" ../nibs-main/src ./src > "$WORK/report.md"
```

The report has a row for each group and a diff for each page that changed, starting from the ones that lost the largest share of their text. It does not decide anything: whether the text that went away was noise or content has to be read from the diffs.

Only reading can be compared this way. A version that asks for an address that was not asked for when the set was made gets "not in the benchmark set" as its answer.
