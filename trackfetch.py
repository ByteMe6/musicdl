#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

import requests
import spotipy
from mutagen.id3 import (
    APIC,
    ID3,
    TALB,
    TDRC,
    TIT2,
    TPE1,
    TPE2,
    TRCK,
)
from spotipy.oauth2 import SpotifyClientCredentials

YTDLP_REMOTE_COMPONENTS = "ejs:github"


def normalize(text: str) -> str:
    """Нормализует текст для сравнения."""
    text = unicodedata.normalize("NFKD", text).lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(
        None,
        normalize(a),
        normalize(b)
    ).ratio()


def sanitize_filename(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    name = re.sub(r"\s+", " ", name).strip()

    # Защита от слишком длинных имён файлов
    return name[:200]


def parse_song(line: str):
    """
    Разделяет строку:
    Artist - Title
    """
    if " - " not in line:
        return None

    artist, title = line.split(" - ", 1)

    artist = artist.strip()
    title = title.strip()

    if not artist or not title:
        return None

    return artist, title


def get_spotify():
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

    if not client_id or not client_secret:
        print("\nERROR: Spotify credentials not found.")
        print("Set:")
        print("export SPOTIFY_CLIENT_ID='...'")
        print("export SPOTIFY_CLIENT_SECRET='...'")
        sys.exit(1)

    return spotipy.Spotify(
        auth_manager=SpotifyClientCredentials(
            client_id=client_id,
            client_secret=client_secret,
        ),
        requests_timeout=30,
        retries=3,
    )


def find_spotify_track(sp, artist: str, title: str):
    """
    Ищет несколько вариантов и выбирает наиболее похожий.
    """

    query = f'artist:"{artist}" track:"{title}"'

    try:
        results = sp.search(
            q=query,
            type="track",
            limit=10,
        )
    except Exception as error:
        print(f"WARNING: Spotify search error: {error}")
        return None

    tracks = results.get("tracks", {}).get("items", [])

    if not tracks:
        # Запасной, менее строгий поиск
        try:
            results = sp.search(
                q=f"{artist} {title}",
                type="track",
                limit=10,
            )
            tracks = results.get("tracks", {}).get("items", [])
        except Exception:
            return None

    if not tracks:
        return None

    best_track = None
    best_score = -1.0

    for track in tracks:
        spotify_title = track["name"]
        spotify_artists = " ".join(
            item["name"]
            for item in track["artists"]
        )

        title_score = similarity(title, spotify_title)
        artist_score = similarity(artist, spotify_artists)

        score = title_score * 0.70 + artist_score * 0.30

        if score > best_score:
            best_score = score
            best_track = track

    print(f"Spotify match score: {best_score:.2f}")

    return best_track


def get_track_metadata(track, fallback_artist, fallback_title):
    """Превращает Spotify-результат в удобный словарь."""

    if track is None:
        return {
            "artist": fallback_artist,
            "title": fallback_title,
            "album": "",
            "album_artist": fallback_artist,
            "track_number": None,
            "release_date": None,
            "cover_url": None,
        }

    artist = ", ".join(
        item["name"]
        for item in track["artists"]
    )

    album = track.get("album", {})

    album_artist = ", ".join(
        item["name"]
        for item in album.get("artists", [])
    )

    images = album.get("images", [])

    return {
        "artist": artist,
        "title": track["name"],
        "album": album.get("name", ""),
        "album_artist": album_artist or artist,
        "track_number": track.get("track_number"),
        "release_date": album.get("release_date"),
        "cover_url": images[0]["url"] if images else None,
    }


def download_cover(url: str, destination: Path):
    response = requests.get(
        url,
        timeout=30,
        headers={
            "User-Agent": "trackfetch/2.0"
        },
    )

    response.raise_for_status()

    destination.write_bytes(response.content)


def youtube_search(query: str, limit: int = 5):
    """
    Получает несколько результатов YouTube в JSON.
    """

    command = [
        "yt-dlp",
        "--remote-components",
        YTDLP_REMOTE_COMPONENTS,
        "--flat-playlist",
        "--dump-json",
        f"ytsearch{limit}:{query}",
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    videos = []

    for line in result.stdout.splitlines():
        try:
            data = json.loads(line)
            videos.append(data)
        except json.JSONDecodeError:
            pass

    return videos


def score_youtube_result(
    video,
    artist: str,
    title: str,
):
    """
    Оценивает, насколько YouTube-видео похоже
    на нужный трек.
    """

    video_title = video.get("title", "")

    title_score = similarity(title, video_title)

    # Насколько имя исполнителя присутствует
    artist_score = similarity(artist, video_title)

    score = (
        title_score * 0.70
        + artist_score * 0.30
    )

    normalized_video = normalize(video_title)

    # Бонус за official audio / topic
    if "official audio" in normalized_video:
        score += 0.08

    if "audio" in normalized_video:
        score += 0.03

    # Штраф за каверы
    bad_words = [
        "cover",
        "караоке",
        "karaoke",
        "nightcore",
        "sped up",
        "slowed",
        "remix",
        "reaction",
    ]

    for word in bad_words:
        if word in normalized_video:
            score -= 0.20

    return score


def find_youtube_video(artist: str, title: str):
    query = f"{artist} {title}"

    print(f"Searching YouTube: {query}")

    videos = youtube_search(query, limit=5)

    if not videos:
        return None

    best_video = None
    best_score = -999.0

    for video in videos:
        score = score_youtube_result(
            video,
            artist,
            title,
        )

        print(
            f"  YouTube score {score:.2f}: "
            f"{video.get('title', 'Unknown')}"
        )

        if score > best_score:
            best_score = score
            best_video = video

    if best_video:
        print(
            f"Selected: "
            f"{best_video.get('title', 'Unknown')}"
        )

    return best_video


def download_audio(
    video_url: str,
    temp_dir: Path,
):
    """
    Скачивает конкретное выбранное видео.
    """

    template = str(temp_dir / "audio.%(ext)s")

    command = [
        "yt-dlp",
        "-x",
        "--audio-format",
        "mp3",
        "--audio-quality",
        "0",
        "--remote-components",
        YTDLP_REMOTE_COMPONENTS,
        "--no-playlist",
        "-o",
        template,
        video_url,
    ]

    result = subprocess.run(command)

    if result.returncode != 0:
        return None

    files = list(temp_dir.glob("audio.mp3"))

    if not files:
        return None

    return files[0]


def add_metadata(
    mp3_path: Path,
    cover_path: Path,
    metadata: dict,
):
    """
    Вшивает нормальные ID3-теги и Spotify cover.
    """

    try:
        audio = ID3(mp3_path)
    except Exception:
        audio = ID3()

    for tag in [
        "APIC",
        "TIT2",
        "TPE1",
        "TALB",
        "TPE2",
        "TRCK",
        "TDRC",
    ]:
        audio.delall(tag)

    audio.add(
        TIT2(
            encoding=3,
            text=metadata["title"],
        )
    )

    audio.add(
        TPE1(
            encoding=3,
            text=metadata["artist"],
        )
    )

    if metadata["album"]:
        audio.add(
            TALB(
                encoding=3,
                text=metadata["album"],
            )
        )

    if metadata["album_artist"]:
        audio.add(
            TPE2(
                encoding=3,
                text=metadata["album_artist"],
            )
        )

    if metadata["track_number"]:
        audio.add(
            TRCK(
                encoding=3,
                text=str(metadata["track_number"]),
            )
        )

    if metadata["release_date"]:
        audio.add(
            TDRC(
                encoding=3,
                text=str(metadata["release_date"]),
            )
        )

    if cover_path.exists():
        image_data = cover_path.read_bytes()

        audio.add(
            APIC(
                encoding=3,
                mime="image/jpeg",
                type=3,
                desc="Cover",
                data=image_data,
            )
        )

    audio.save(
        mp3_path,
        v2_version=3,
    )


def make_filename(metadata, title_only):
    if title_only:
        name = metadata["title"]
    else:
        name = (
            f"{metadata['artist']} - "
            f"{metadata['title']}"
        )

    return sanitize_filename(name) + ".mp3"


def read_done(done_file: Path):
    if not done_file.exists():
        return set()

    return {
        line.strip()
        for line in done_file.read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines()
        if line.strip()
    }


def append_line(path: Path, text: str):
    with path.open(
        "a",
        encoding="utf-8",
    ) as file:
        file.write(text + "\n")


def process_song(
    sp,
    input_artist,
    input_title,
    output,
    title_only,
):
    track = find_spotify_track(
        sp,
        input_artist,
        input_title,
    )

    metadata = get_track_metadata(
        track,
        input_artist,
        input_title,
    )

    print(
        f"Metadata: "
        f"{metadata['artist']} - "
        f"{metadata['title']}"
    )

    filename = make_filename(
        metadata,
        title_only,
    )

    final_path = output / filename

    if final_path.exists():
        print(f"SKIP: already exists: {filename}")
        return True, "exists"

    video = find_youtube_video(
        metadata["artist"],
        metadata["title"],
    )

    if not video:
        print("FAILED: No YouTube result")
        return False, "no YouTube result"

    video_url = (
        video.get("webpage_url")
        or video.get("url")
    )

    if not video_url:
        video_id = video.get("id")

        if video_id:
            video_url = (
                "https://www.youtube.com/watch?v="
                + video_id
            )

    if not video_url:
        print("FAILED: Invalid YouTube result")
        return False, "invalid YouTube result"

    with tempfile.TemporaryDirectory() as temp:
        temp_dir = Path(temp)

        mp3_path = download_audio(
            video_url,
            temp_dir,
        )

        if not mp3_path:
            return False, "yt-dlp download failed"

        cover_path = temp_dir / "cover.jpg"

        if metadata["cover_url"]:
            try:
                download_cover(
                    metadata["cover_url"],
                    cover_path,
                )

                print("Spotify cover downloaded")

            except Exception as error:
                print(
                    f"WARNING: cover download failed: "
                    f"{error}"
                )

        try:
            add_metadata(
                mp3_path,
                cover_path,
                metadata,
            )

        except Exception as error:
            return False, f"metadata error: {error}"

        try:
            shutil.move(
                str(mp3_path),
                str(final_path),
            )

        except Exception as error:
            return False, f"move error: {error}"

    print(f"SUCCESS: {filename}")

    return True, "downloaded"


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Download music using Spotify metadata "
            "and YouTube audio"
        )
    )

    parser.add_argument(
        "input",
        type=Path,
        help="Text file with Artist - Title",
    )

    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path.home() / "Music" / "trackfetch",
        help="Output directory",
    )

    parser.add_argument(
        "--title-only",
        action="store_true",
        help="Use only title in filename",
    )

    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay between songs in seconds",
    )

    args = parser.parse_args()

    if not args.input.exists():
        print(f"ERROR: Input file not found: {args.input}")
        sys.exit(1)

    args.output.mkdir(
        parents=True,
        exist_ok=True,
    )

    done_file = args.output / "done.txt"
    failed_file = args.output / "failed.txt"

    songs = []

    for line in args.input.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines():

        line = line.strip()

        if not line or line.startswith("#"):
            continue

        song = parse_song(line)

        if song:
            songs.append(song)

    done = read_done(done_file)

    print(f"Found {len(songs)} songs")
    print(f"Already completed: {len(done)}")
    print(f"Output: {args.output}")

    sp = get_spotify()

    success = 0
    skipped = 0
    failed = 0

    for number, (artist, title) in enumerate(
        songs,
        start=1,
    ):
        song_key = f"{artist} - {title}"

        print()
        print("=" * 60)
        print(f"[{number}/{len(songs)}]")
        print(song_key)

        if song_key in done:
            print("SKIP: already completed")
            skipped += 1
            continue

        ok, reason = process_song(
            sp,
            artist,
            title,
            args.output,
            args.title_only,
        )

        if ok:
            append_line(
                done_file,
                song_key,
            )

            success += 1

            if reason == "exists":
                skipped += 1

        else:
            append_line(
                failed_file,
                f"{song_key} | {reason}",
            )

            failed += 1

        if number < len(songs):
            time.sleep(args.delay)

    print()
    print("=" * 60)
    print("FINISHED")
    print(f"SUCCESS: {success}")
    print(f"SKIPPED: {skipped}")
    print(f"FAILED: {failed}")
    print(f"DONE FILE: {done_file}")
    print(f"FAILED FILE: {failed_file}")


if __name__ == "__main__":
    main()
