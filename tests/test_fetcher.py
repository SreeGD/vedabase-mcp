"""Tests for reference parsing and API data extraction."""

import pytest

from vedabase_mcp.fetcher import parse_verse_ref, make_ref, _extract_prabhupada_translation


class TestParseVerseRef:
    def test_standard_format(self):
        assert parse_verse_ref("BG 2.47") == (2, 47)

    def test_lowercase(self):
        assert parse_verse_ref("bg 2.47") == (2, 47)

    def test_no_prefix(self):
        assert parse_verse_ref("2.47") == (2, 47)

    def test_colon_separator(self):
        assert parse_verse_ref("2:47") == (2, 47)

    def test_dash_separator(self):
        assert parse_verse_ref("15-7") == (15, 7)

    def test_gita_prefix(self):
        assert parse_verse_ref("Gita 9.34") == (9, 34)

    def test_bhagavad_gita_prefix(self):
        assert parse_verse_ref("Bhagavad Gita 9.34") == (9, 34)

    def test_bhagavad_gita_hyphenated(self):
        assert parse_verse_ref("Bhagavad-Gita 9.34") == (9, 34)

    def test_bg_with_colon(self):
        assert parse_verse_ref("BG 9:34") == (9, 34)

    def test_spaces_around_separator(self):
        assert parse_verse_ref("BG 2 . 47") == (2, 47)

    def test_invalid_no_numbers(self):
        with pytest.raises(ValueError):
            parse_verse_ref("hello")

    def test_invalid_chapter_zero(self):
        with pytest.raises(ValueError):
            parse_verse_ref("0.1")

    def test_invalid_chapter_19(self):
        with pytest.raises(ValueError):
            parse_verse_ref("19.1")

    def test_invalid_verse_too_high(self):
        # Chapter 1 has 47 verses
        with pytest.raises(ValueError):
            parse_verse_ref("1.48")

    def test_chapter_18_last_verse(self):
        assert parse_verse_ref("18.78") == (18, 78)


class TestMakeRef:
    def test_standard(self):
        assert make_ref(2, 47) == "BG 2.47"

    def test_chapter_18(self):
        assert make_ref(18, 78) == "BG 18.78"


class TestExtractPrabhupadaTranslation:
    def test_prabhu_key_flat(self):
        data = {"prabhu": {"author": "Swami Prabhupada", "et": "Translation text"}}
        assert _extract_prabhupada_translation(data) == "Translation text"

    def test_prabhu_key_nested(self):
        data = {"commentaries": {"prabhu": {"author": "Swami Prabhupada", "et": "Nested text"}}}
        assert _extract_prabhupada_translation(data) == "Nested text"

    def test_spiurp_key_flat(self):
        data = {"spiurp": {"author": "Srila Prabhupada", "et": "Alt key text"}}
        assert _extract_prabhupada_translation(data) == "Alt key text"

    def test_missing_key(self):
        data = {"gambir": {"author": "Gambirananda", "et": "Other text"}}
        assert _extract_prabhupada_translation(data) is None

    def test_hindi_fallback(self):
        data = {"prabhu": {"author": "Prabhupada", "ht": "Hindi text"}}
        assert _extract_prabhupada_translation(data) == "Hindi text"
