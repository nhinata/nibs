# Contributing

## Development

```sh
python -m venv .venv
.venv/bin/pip install -e . pytest
.venv/bin/pytest -q
```

The tests do not reach the internet: they serve pages from a fake site (`tests/conftest.py`) or from a web server on localhost (`tests/test_fetch.py`).

## Code

### Names

These apply to the code in `src/` and `benchmark/`.

- A function or method starts with a verb; one verb is enough when it says what the function does.
- A function that returns true or false starts with `is_`.
- A class is named with a noun for what it is.
- No name joins two things with a preposition.
- The function that runs a command has the command's name, even when it is not a verb.
- Names that something outside nibs decides are kept: the function a script or `pyproject.toml` starts from, and the methods a base class calls.

Test functions are named `test_` and the behavior they check, written as a sentence; fixtures are named by what they give the test.

### Modules

In `src/nibs/`, messages to the user (errors, guidance and what a command prints) are written only in `cli.py`. The other modules give data back and print nothing.

## Pull requests

- **One topic per pull request.** Name the branch `<type>/<topic>`, such as `fix/sphinx-headings`.
- **Titles follow [Conventional Commits](https://www.conventionalcommits.org/).** Pull requests are squash-merged, so the title becomes the commit on `main`, and the release tooling reads it to pick the next version:

  | Prefix | Use for | Version bump |
  | --- | --- | --- |
  | `feat:` | a new command, option or output | minor |
  | `fix:` | wrong output or a crash | patch |
  | `feat!:` / `fix!:` | a change to the output or to a command that breaks instructions written for the old one | major (minor while 0.x) |
  | `docs:`, `test:`, `refactor:`, `ci:`, `chore:` | everything else | none |

- `main` is protected: every change goes through a pull request, and the tests must pass.

## Releases

Merging a pull request that bumps the version makes release-please open a release pull request. Merging that publishes the version to PyPI ([release.yml](.github/workflows/release.yml)).
