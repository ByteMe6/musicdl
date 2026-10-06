import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def make_track(
    name="Song",
    artists=("Artist",),
    album="Album",
    album_artists=None,
    track_number=3,
    release_date="2001-03-12",
    images=({"url": "https://img/640.jpg"},),
):
    """Minimal Spotify track object with the fields trackfetch reads."""
    album_artists = artists if album_artists is None else album_artists
    return {
        "name": name,
        "artists": [{"name": a} for a in artists],
        "track_number": track_number,
        "album": {
            "name": album,
            "artists": [{"name": a} for a in album_artists],
            "release_date": release_date,
            "images": list(images),
        },
    }


class FakeSpotify:
    """Returns queued responses from search() and records the queries."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.queries = []

    def search(self, q, type, limit):
        self.queries.append(q)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return {"tracks": {"items": response}}


@pytest.fixture
def metadata():
    return {
        "artist": "Daft Punk",
        "title": "One More Time",
        "album": "Discovery",
        "album_artist": "Daft Punk",
        "track_number": 1,
        "release_date": "2001-03-12",
        "cover_url": "https://img/cover.jpg",
    }
