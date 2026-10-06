# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Ukrainian and Russian translations of the README.
- A section on exporting playlists from Spotify, Apple Music, YouTube Music and other services with TuneMyMusic.
- A tldr page in `docs/tldr/musicdl.md`.
- Offline pytest suite (81 tests, 100% coverage) that runs in CI on Linux, macOS and Windows.

### Changed
- musicdl is now licensed under the GPL-3.0-or-later instead of MIT. Version 1.0.0 remains available under MIT.

## [1.0.0] - 2026-10-06

### Added
- Batch download from a text file of `Artist - Title` lines, with `#` comments and blank lines ignored.
- Spotify metadata lookup with strict and loose search plus fuzzy best-match scoring.
- Scored YouTube candidate selection that prefers official audio and penalises covers, karaoke, nightcore, sped-up and slowed edits, remixes and reaction videos.
- Best-quality MP3 extraction through yt-dlp and FFmpeg.
- ID3v2.3 tags: title, artist, album, album artist, track number, release date and embedded front cover.
- Resumable runs via `done.txt`, and a failure log with reasons in `failed.txt`.
- `--output`, `--title-only` and `--delay` options.
- PyInstaller spec, plus prebuilt binaries for Linux, macOS and Windows on x86_64 and ARM64.
- Automated releases: pushing a new version to `master` builds and publishes all binaries.

[1.0.0]: https://github.com/ByteMe6/musicdl/releases/tag/v1.0.0
