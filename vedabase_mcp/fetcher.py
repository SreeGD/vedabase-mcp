"""HTTP client for vedicscriptures.github.io API and vedabase.io scraper."""

import json
import logging
import re

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

API_BASE = "https://vedicscriptures.github.io"
VEDABASE_BASE = "https://vedabase.io/en/library/bg"

# Chapter verse counts for seeding (BG chapters 1-18)
CHAPTER_VERSE_COUNTS = [
    47, 72, 43, 42, 29, 47, 30, 28, 34, 42,
    55, 20, 35, 27, 20, 24, 28, 78,
]

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


def parse_verse_ref(reference: str) -> tuple[int, int]:
    """Parse a verse reference string into (chapter, verse).

    Accepts: "BG 2.47", "2:47", "bg 15-7", "Bhagavad Gita 9.34", etc.
    Raises ValueError for invalid formats.
    """
    text = reference.strip()
    # Strip optional prefix
    text = re.sub(
        r"^(bhagavad[\s-]*gita|gita|bg)\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )
    # Split on . or : or -
    match = re.match(r"(\d+)\s*[.:\-]\s*(\d+)", text)
    if not match:
        raise ValueError(f"Invalid verse reference: {reference!r}")
    chapter, verse = int(match.group(1)), int(match.group(2))
    if not (1 <= chapter <= 18):
        raise ValueError(f"Chapter must be 1-18, got {chapter}")
    if not (1 <= verse <= CHAPTER_VERSE_COUNTS[chapter - 1]):
        raise ValueError(
            f"Chapter {chapter} has {CHAPTER_VERSE_COUNTS[chapter - 1]} verses, "
            f"got verse {verse}"
        )
    return chapter, verse


def make_ref(chapter: int, verse: int) -> str:
    """Create a canonical reference string like 'BG 2.47'."""
    return f"BG {chapter}.{verse}"


def vedabase_url(chapter: int, verse: int) -> str:
    """Construct the vedabase.io URL for a verse."""
    return f"{VEDABASE_BASE}/{chapter}/{verse}/"


async def fetch_verse_api(chapter: int, verse: int) -> dict:
    """Fetch a single verse from the vedicscriptures API."""
    url = f"{API_BASE}/slok/{chapter}/{verse}"
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()


async def fetch_chapter_api(chapter: int) -> dict:
    """Fetch chapter metadata from the vedicscriptures API."""
    url = f"{API_BASE}/chapter/{chapter}"
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()


async def fetch_all_chapters_api() -> list[dict]:
    """Fetch all chapter metadata from the vedicscriptures API."""
    url = f"{API_BASE}/chapters"
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()


def _extract_prabhupada_translation(api_data: dict) -> str | None:
    """Extract Prabhupada's translation from the API response."""
    # The API nests commentaries under various keys
    # Try 'prabhu' first (as seen in actual API), then 'spiurp' (spec mentions this)
    for key in ("prabhu", "spiurp"):
        author_data = api_data.get(key) or api_data.get("commentaries", {}).get(key)
        if author_data:
            return author_data.get("et") or author_data.get("ht")
    return None


async def fetch_verse_vedabase(chapter: int, verse: int) -> dict:
    """Scrape vedabase.io for Prabhupada's synonyms, translation, and purport.

    Returns {"synonyms": str|None, "translation": str|None, "purport": str|None}.
    Returns empty values on failure (Cloudflare block, network error, etc.).
    """
    url = vedabase_url(chapter, verse)
    result = {"synonyms": None, "translation": None, "purport": None}
    try:
        async with httpx.AsyncClient(timeout=30, headers=_HEADERS, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            html = resp.text

        soup = BeautifulSoup(html, "lxml")

        # Synonyms
        syn_div = soup.select_one(".av-synonyms")
        if syn_div:
            result["synonyms"] = syn_div.get_text(separator=" ", strip=True)

        # Translation
        trans_div = soup.select_one(".av-translation")
        if trans_div:
            result["translation"] = trans_div.get_text(strip=True)

        # Purport
        purport_div = soup.select_one(".av-purport")
        if purport_div:
            result["purport"] = purport_div.get_text(separator="\n\n", strip=True)

    except Exception as e:
        logger.warning("Failed to scrape vedabase.io for BG %d.%d: %s", chapter, verse, e)

    return result


def _parse_api_verse(api_data: dict, chapter: int, verse: int) -> dict:
    """Parse API response into our verse dict format."""
    return {
        "ref": make_ref(chapter, verse),
        "chapter": chapter,
        "verse": verse,
        "devanagari": api_data.get("slok"),
        "transliteration": api_data.get("transliteration"),
        "synonyms": None,
        "translation": _extract_prabhupada_translation(api_data),
        "purport": None,
        "vedabase_url": vedabase_url(chapter, verse),
        "raw_json": json.dumps(api_data, ensure_ascii=False),
    }


async def fetch_verse(chapter: int, verse: int, enrich: bool = True) -> dict:
    """Fetch verse from API and optionally enrich with vedabase.io data.

    Args:
        chapter: Chapter number (1-18)
        verse: Verse number
        enrich: If True, also scrape vedabase.io for synonyms/purport

    Returns:
        Verse dict ready for upsert_verse()
    """
    api_data = await fetch_verse_api(chapter, verse)
    verse_data = _parse_api_verse(api_data, chapter, verse)

    if enrich:
        vedabase_data = await fetch_verse_vedabase(chapter, verse)
        if vedabase_data["synonyms"]:
            verse_data["synonyms"] = vedabase_data["synonyms"]
        if vedabase_data["translation"]:
            verse_data["translation"] = vedabase_data["translation"]
        if vedabase_data["purport"]:
            verse_data["purport"] = vedabase_data["purport"]

    return verse_data


def parse_chapter_api(api_data: dict) -> dict:
    """Parse chapter API response into our chapter dict format."""
    meaning = api_data.get("meaning", {})
    summary = api_data.get("summary", {})
    return {
        "chapter_number": api_data["chapter_number"],
        "name": api_data.get("name"),
        "name_transliterated": api_data.get("transliteration"),
        "name_meaning": meaning.get("en", "") if isinstance(meaning, dict) else str(meaning),
        "verses_count": api_data.get("verses_count"),
        "summary": summary.get("en", "") if isinstance(summary, dict) else str(summary),
        "raw_json": json.dumps(api_data, ensure_ascii=False),
    }
