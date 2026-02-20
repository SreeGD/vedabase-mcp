"""SQLite cache for Bhagavad Gita verses and chapters."""

import json
import os
import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = os.path.join(Path.home(), ".vedabase_mcp", "cache.db")


def _db_path() -> str:
    return os.environ.get("VEDABASE_DB_PATH", DEFAULT_DB_PATH)


def init_db() -> sqlite3.Connection:
    """Create tables and indexes, set WAL mode. Returns a connection."""
    path = _db_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS verses (
            ref              TEXT PRIMARY KEY,
            chapter          INTEGER NOT NULL,
            verse            INTEGER NOT NULL,
            devanagari       TEXT,
            transliteration  TEXT,
            synonyms         TEXT,
            translation      TEXT,
            purport          TEXT,
            vedabase_url     TEXT,
            raw_json         TEXT,
            fetched_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS chapters (
            chapter_number      INTEGER PRIMARY KEY,
            name                TEXT,
            name_transliterated TEXT,
            name_meaning        TEXT,
            verses_count        INTEGER,
            summary             TEXT,
            raw_json            TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_verses_chapter ON verses(chapter);
        CREATE INDEX IF NOT EXISTS idx_verses_transliteration ON verses(transliteration);
    """)
    conn.commit()
    return conn


def get_verse(conn: sqlite3.Connection, ref: str) -> dict | None:
    """Retrieve a cached verse by reference (e.g. 'BG 2.47')."""
    row = conn.execute("SELECT * FROM verses WHERE ref = ?", (ref,)).fetchone()
    return dict(row) if row else None


def upsert_verse(conn: sqlite3.Connection, data: dict) -> None:
    """Insert or update a verse in the cache."""
    conn.execute(
        """INSERT OR REPLACE INTO verses
           (ref, chapter, verse, devanagari, transliteration,
            synonyms, translation, purport, vedabase_url, raw_json, fetched_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
        (
            data["ref"],
            data["chapter"],
            data["verse"],
            data.get("devanagari"),
            data.get("transliteration"),
            data.get("synonyms"),
            data.get("translation"),
            data.get("purport"),
            data.get("vedabase_url"),
            data.get("raw_json"),
        ),
    )
    conn.commit()


def search_verses(
    conn: sqlite3.Connection, query: str, max_results: int = 5
) -> list[dict]:
    """Keyword search across transliteration, translation, and devanagari."""
    pattern = f"%{query}%"
    rows = conn.execute(
        """SELECT ref, chapter, verse, transliteration, translation
           FROM verses
           WHERE transliteration LIKE ? OR translation LIKE ? OR devanagari LIKE ?
           LIMIT ?""",
        (pattern, pattern, pattern, max_results),
    ).fetchall()
    return [dict(r) for r in rows]


def get_all_transliterations(conn: sqlite3.Connection) -> list[tuple[str, str]]:
    """Return (ref, transliteration) for all cached verses. Used for fuzzy matching."""
    rows = conn.execute(
        "SELECT ref, transliteration FROM verses WHERE transliteration IS NOT NULL"
    ).fetchall()
    return [(r["ref"], r["transliteration"]) for r in rows]


def get_chapter(conn: sqlite3.Connection, chapter_number: int) -> dict | None:
    """Retrieve cached chapter metadata."""
    row = conn.execute(
        "SELECT * FROM chapters WHERE chapter_number = ?", (chapter_number,)
    ).fetchone()
    return dict(row) if row else None


def upsert_chapter(conn: sqlite3.Connection, data: dict) -> None:
    """Insert or update chapter metadata."""
    conn.execute(
        """INSERT OR REPLACE INTO chapters
           (chapter_number, name, name_transliterated, name_meaning,
            verses_count, summary, raw_json)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            data["chapter_number"],
            data.get("name"),
            data.get("name_transliterated"),
            data.get("name_meaning"),
            data.get("verses_count"),
            data.get("summary"),
            data.get("raw_json"),
        ),
    )
    conn.commit()


def verse_count(conn: sqlite3.Connection) -> int:
    """Return total number of cached verses."""
    row = conn.execute("SELECT COUNT(*) as cnt FROM verses").fetchone()
    return row["cnt"]
