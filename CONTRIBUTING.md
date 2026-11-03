# Contributing

## Development

```sh
python -m venv .venv
.venv/bin/pip install -e . pytest
.venv/bin/pytest -q
```

The tests do not touch the network; they serve pages from a fake site (`tests/conftest.py`).

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
