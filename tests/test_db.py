"""Tests for SQLite database operations."""

import os
import tempfile

import pytest

from vedabase_mcp import db


@pytest.fixture
def tmp_db(monkeypatch):
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test.db")
        monkeypatch.setenv("VEDABASE_DB_PATH", path)
        conn = db.init_db()
        yield conn
        conn.close()


class TestInitDb:
    def test_creates_tables(self, tmp_db):
        tables = tmp_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        names = {r["name"] for r in tables}
        assert "verses" in names
        assert "chapters" in names

    def test_wal_mode(self, tmp_db):
        mode = tmp_db.execute("PRAGMA journal_mode").fetchone()
        assert mode[0] == "wal"


class TestVerseOperations:
    SAMPLE_VERSE = {
        "ref": "BG 2.47",
        "chapter": 2,
        "verse": 47,
        "devanagari": "कर्मण्येवाधिकारस्ते",
        "transliteration": "karmaṇyevādhikāraste mā phaleṣu kadācana",
        "synonyms": "karmaṇi — work; eva — only",
        "translation": "You have a right to perform your prescribed duty",
        "purport": "This is the purport text.",
        "vedabase_url": "https://vedabase.io/en/library/bg/2/47/",
        "raw_json": "{}",
    }

    def test_upsert_and_get(self, tmp_db):
        db.upsert_verse(tmp_db, self.SAMPLE_VERSE)
        result = db.get_verse(tmp_db, "BG 2.47")
        assert result is not None
        assert result["ref"] == "BG 2.47"
        assert result["chapter"] == 2
        assert result["translation"] == "You have a right to perform your prescribed duty"

    def test_get_nonexistent(self, tmp_db):
        assert db.get_verse(tmp_db, "BG 99.99") is None

    def test_upsert_replaces(self, tmp_db):
        db.upsert_verse(tmp_db, self.SAMPLE_VERSE)
        updated = {**self.SAMPLE_VERSE, "translation": "Updated translation"}
        db.upsert_verse(tmp_db, updated)
        result = db.get_verse(tmp_db, "BG 2.47")
        assert result["translation"] == "Updated translation"

    def test_verse_count(self, tmp_db):
        assert db.verse_count(tmp_db) == 0
        db.upsert_verse(tmp_db, self.SAMPLE_VERSE)
        assert db.verse_count(tmp_db) == 1


class TestSearch:
    def test_search_by_transliteration(self, tmp_db):
        db.upsert_verse(tmp_db, {
            "ref": "BG 2.47", "chapter": 2, "verse": 47,
            "transliteration": "karmaṇyevādhikāraste",
            "translation": "You have a right",
        })
        results = db.search_verses(tmp_db, "karma")
        assert len(results) == 1
        assert results[0]["ref"] == "BG 2.47"

    def test_search_by_translation(self, tmp_db):
        db.upsert_verse(tmp_db, {
            "ref": "BG 9.34", "chapter": 9, "verse": 34,
            "transliteration": "manmanā bhava",
            "translation": "Always think of Me and surrender",
        })
        results = db.search_verses(tmp_db, "surrender")
        assert len(results) == 1
        assert results[0]["ref"] == "BG 9.34"

    def test_search_no_results(self, tmp_db):
        results = db.search_verses(tmp_db, "nonexistent")
        assert results == []

    def test_search_max_results(self, tmp_db):
        for i in range(1, 6):
            db.upsert_verse(tmp_db, {
                "ref": f"BG 1.{i}", "chapter": 1, "verse": i,
                "transliteration": "common word",
                "translation": "common text",
            })
        results = db.search_verses(tmp_db, "common", max_results=3)
        assert len(results) == 3


class TestTransliterations:
    def test_get_all_transliterations(self, tmp_db):
        db.upsert_verse(tmp_db, {
            "ref": "BG 2.47", "chapter": 2, "verse": 47,
            "transliteration": "karmaṇyevādhikāraste",
        })
        db.upsert_verse(tmp_db, {
            "ref": "BG 9.34", "chapter": 9, "verse": 34,
            "transliteration": "manmanā bhava madbhakto",
        })
        result = db.get_all_transliterations(tmp_db)
        assert len(result) == 2
        refs = {r[0] for r in result}
        assert "BG 2.47" in refs
        assert "BG 9.34" in refs


class TestChapterOperations:
    SAMPLE_CHAPTER = {
        "chapter_number": 2,
        "name": "सांख्ययोग",
        "name_transliterated": "Sānkhya Yog",
        "name_meaning": "Contents of the Gītā Summarized",
        "verses_count": 72,
        "summary": "Chapter 2 summary.",
        "raw_json": "{}",
    }

    def test_upsert_and_get(self, tmp_db):
        db.upsert_chapter(tmp_db, self.SAMPLE_CHAPTER)
        result = db.get_chapter(tmp_db, 2)
        assert result is not None
        assert result["name"] == "सांख्ययोग"
        assert result["verses_count"] == 72

    def test_get_nonexistent(self, tmp_db):
        assert db.get_chapter(tmp_db, 99) is None
