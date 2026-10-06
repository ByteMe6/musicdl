import pytest

import trackfetch as m


class TestNormalize:
    def test_lowercases_and_strips_punctuation(self):
        assert m.normalize("Harder, Better, Faster!") == "harder better faster"

    def test_collapses_whitespace(self):
        assert m.normalize("  a \t  b\n c  ") == "a b c"

    def test_keeps_cyrillic(self):
        assert m.normalize("Мёртвый Анархист") == m.normalize("мёртвый анархист")

    def test_empty(self):
        assert m.normalize("") == ""


class TestSimilarity:
    def test_identical_ignoring_case_and_punctuation(self):
        assert m.similarity("One More Time!", "one more time") == 1.0

    def test_unrelated_is_low(self):
        assert m.similarity("Paranoid Android", "Bohemian Rhapsody") < 0.5

    def test_symmetric(self):
        assert m.similarity("abc def", "abc") == pytest.approx(m.similarity("abc", "abc def"))


class TestSanitizeFilename:
    def test_replaces_illegal_characters(self):
        assert m.sanitize_filename('AC/DC: "Back" <In> Black?') == "AC_DC_ _Back_ _In_ Black_"

    def test_replaces_backslash_pipe_star_and_control_chars(self):
        assert m.sanitize_filename("a\\b|c*d\x00e\x1f") == "a_b_c_d_e_"

    def test_collapses_and_trims_whitespace(self):
        assert m.sanitize_filename("  a   b  ") == "a b"

    def test_truncates_to_200(self):
        assert len(m.sanitize_filename("x" * 500)) == 200

    def test_keeps_unicode(self):
        assert m.sanitize_filename("Severny Flot - ИNОЙ") == "Severny Flot - ИNОЙ"


class TestParseSong:
    @pytest.mark.parametrize(
        ("line", "expected"),
        [
            ("Daft Punk - One More Time", ("Daft Punk", "One More Time")),
            ("  Artist   -   Title  ", ("Artist", "Title")),
            ("A - B - C", ("A", "B - C")),
            ("Jay-Z - 99 Problems", ("Jay-Z", "99 Problems")),
            ("Korol i Shut - Мёртвый Анархист", ("Korol i Shut", "Мёртвый Анархист")),
        ],
    )
    def test_valid(self, line, expected):
        assert m.parse_song(line) == expected

    @pytest.mark.parametrize("line", ["no separator", "Artist-Title", " - Title", "Artist - ", ""])
    def test_invalid(self, line):
        assert m.parse_song(line) is None


class TestMakeFilename:
    def test_artist_and_title(self, metadata):
        assert m.make_filename(metadata, title_only=False) == "Daft Punk - One More Time.mp3"

    def test_title_only(self, metadata):
        assert m.make_filename(metadata, title_only=True) == "One More Time.mp3"

    def test_sanitized(self, metadata):
        metadata["artist"] = "AC/DC"
        assert m.make_filename(metadata, title_only=False) == "AC_DC - One More Time.mp3"
