import pytest
from mutagen.id3 import ID3, TIT2

import musicdl as m

JPEG = b"\xff\xd8\xff\xe0fake-jpeg"


@pytest.fixture
def mp3(tmp_path):
    path = tmp_path / "song.mp3"
    path.write_bytes(b"\x00" * 64)
    return path


class TestAddMetadata:
    def test_writes_all_frames(self, mp3, tmp_path, metadata):
        cover = tmp_path / "cover.jpg"
        cover.write_bytes(JPEG)
        m.add_metadata(mp3, cover, metadata)

        tags = ID3(mp3)
        assert tags.version[:2] == (2, 3)
        assert tags["TIT2"].text == ["One More Time"]
        assert tags["TPE1"].text == ["Daft Punk"]
        assert tags["TALB"].text == ["Discovery"]
        assert tags["TPE2"].text == ["Daft Punk"]
        assert tags["TRCK"].text == ["1"]
        assert str(tags["TDRC"].text[0]) == "2001-03-12"
        apic = tags.getall("APIC")[0]
        assert apic.data == JPEG
        assert apic.type == 3
        assert apic.mime == "image/jpeg"

    def test_skips_empty_optional_fields(self, mp3, tmp_path):
        meta = m.get_track_metadata(None, "Artist", "Title")
        meta["album_artist"] = ""
        m.add_metadata(mp3, tmp_path / "missing.jpg", meta)

        tags = ID3(mp3)
        assert tags["TIT2"].text == ["Title"]
        for frame in ("TALB", "TPE2", "TRCK", "TDRC", "APIC"):
            assert not tags.getall(frame), frame

    def test_replaces_existing_tags(self, mp3, tmp_path, metadata):
        old = ID3()
        old.add(TIT2(encoding=3, text="Old title"))
        old.save(mp3)

        m.add_metadata(mp3, tmp_path / "missing.jpg", metadata)
        assert ID3(mp3).getall("TIT2")[0].text == ["One More Time"]

    def test_unicode(self, mp3, tmp_path, metadata):
        metadata.update(artist="Korol i Shut", title="Мёртвый Анархист")
        m.add_metadata(mp3, tmp_path / "missing.jpg", metadata)
        assert ID3(mp3)["TIT2"].text == ["Мёртвый Анархист"]


class TestDownloadCover:
    def test_writes_bytes(self, monkeypatch, tmp_path):
        class Response:
            content = JPEG

            def raise_for_status(self):
                pass

        seen = {}

        def fake_get(url, timeout, headers):
            seen.update(url=url, timeout=timeout)
            return Response()

        monkeypatch.setattr(m.requests, "get", fake_get)
        dest = tmp_path / "cover.jpg"
        m.download_cover("https://img/x.jpg", dest)
        assert dest.read_bytes() == JPEG
        assert seen == {"url": "https://img/x.jpg", "timeout": 30}

    def test_raises_on_http_error(self, monkeypatch, tmp_path):
        class Response:
            def raise_for_status(self):
                raise m.requests.HTTPError("404")

        monkeypatch.setattr(m.requests, "get", lambda *a, **k: Response())
        with pytest.raises(m.requests.HTTPError):
            m.download_cover("u", tmp_path / "c.jpg")


class TestDoneFile:
    def test_missing_file(self, tmp_path):
        assert m.read_done(tmp_path / "done.txt") == set()

    def test_append_and_read_roundtrip(self, tmp_path):
        done = tmp_path / "done.txt"
        m.append_line(done, "A - B")
        m.append_line(done, "Кино - Группа крови")
        assert done.read_text(encoding="utf-8") == "A - B\nКино - Группа крови\n"
        assert m.read_done(done) == {"A - B", "Кино - Группа крови"}

    def test_ignores_blank_lines_and_whitespace(self, tmp_path):
        done = tmp_path / "done.txt"
        done.write_text("  A - B  \n\n\nC - D\n", encoding="utf-8")
        assert m.read_done(done) == {"A - B", "C - D"}
