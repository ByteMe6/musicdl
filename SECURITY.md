# Security policy

## Supported versions

Only the [latest release](https://github.com/ByteMe6/musicdl/releases/latest) receives fixes.

## Reporting a vulnerability

Please **don't open a public issue**. Report it privately instead:

1. Go to [Security → Report a vulnerability](https://github.com/ByteMe6/musicdl/security/advisories/new).
2. Describe the problem, the affected version and how to reproduce it.

You'll get a reply within 7 days. Once a fix is released, the advisory is published with credit to you, unless you'd rather stay anonymous.

## Your Spotify credentials

musicdl reads `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` from the environment, and Spotipy caches an access token in a `.cache` file in the working directory. Never paste either one into an issue, and never commit `.cache`. If you leak them, rotate the secret in the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard).
