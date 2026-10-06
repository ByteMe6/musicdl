# Contributing to musicdl

Thanks for helping out. Bug reports, matching improvements, docs fixes and translations are all welcome.

## Reporting a wrong match

Most bugs are a wrong song being picked. To make these fixable, include in the [bug report](https://github.com/ByteMe6/musicdl/issues/new?template=bug_report.yml):

- the exact `Artist - Title` line from your input file,
- the `Spotify match score` and `YouTube score` lines from the output,
- which result you expected instead.

## Development setup

```bash
git clone https://github.com/ByteMe6/musicdl.git
cd musicdl
python -m venv .venv && source .venv/bin/activate
pip install -e ".[test]" ruff
```

## Before you open a pull request

```bash
ruff check .            # lint
ruff format --check .   # formatting
pytest --cov=musicdl    # tests, offline, under a second
```

- The test suite stubs every network and subprocess call. Keep it that way: tests must never reach Spotify or YouTube.
- Add a test for every bug fix and every new behaviour. CI fails below 95% coverage.
- Keep pull requests focused on one change, and describe what changed and why.
- Add a line under `## [Unreleased]` in [`CHANGELOG.md`](CHANGELOG.md) for anything a user would notice.

## Changing the matching scores

The weights and keyword penalties in `score_youtube_result` and `find_spotify_track` decide which song gets downloaded. If you change them, explain in the pull request which inputs got better, and add those inputs as test cases so they stay fixed.

## Translations

The README exists in [English](README.md), [Ukrainian](README.uk.md) and [Russian](README.ru.md). If you change the English README, update the translations too, or mention in the pull request that they need updating.

## Releases

Maintainers release by bumping `version` in `pyproject.toml` on `master`. See [Releasing](README.md#releasing).

## License

By contributing, you agree that your contributions are licensed under the [GPL-3.0-or-later](LICENSE), the same license as the project.

## Code of conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). By taking part, you agree to uphold it.
