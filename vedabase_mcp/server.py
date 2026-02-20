"""Vedabase MCP Server — 5 tools for Bhagavad Gita verse lookup and matching."""

import logging

from mcp.server.fastmcp import FastMCP

from vedabase_mcp.db import (
    get_all_transliterations,
    get_verse,
    init_db,
    search_verses as db_search,
    upsert_chapter,
    upsert_verse,
    verse_count,
)
from vedabase_mcp.fetcher import (
    CHAPTER_VERSE_COUNTS,
    fetch_chapter_api,
    fetch_verse,
    make_ref,
    parse_chapter_api,
    parse_verse_ref,
    vedabase_url,
)
from vedabase_mcp.fuzzy import fuzzy_match

logger = logging.getLogger(__name__)

mcp = FastMCP("vedabase")


def _format_verse(v: dict) -> str:
    """Format a verse dict as markdown."""
    parts = [f"## {v['ref']}\n"]

    if v.get("devanagari"):
        parts.append(f"**Sanskrit:**\n{v['devanagari']}\n")

    if v.get("transliteration"):
        parts.append(f"**Transliteration:**\n_{v['transliteration']}_\n")

    if v.get("synonyms"):
        parts.append(f"**Synonyms:**\n{v['synonyms']}\n")

    if v.get("translation"):
        parts.append(f"**Translation (Srila Prabhupada):**\n{v['translation']}\n")

    if v.get("purport"):
        purport = v["purport"]
        # Truncate long purports for tool output
        if len(purport) > 2000:
            purport = purport[:2000] + "...\n\n_(Purport truncated. See full text on Vedabase.)_"
        parts.append(f"**Purport:**\n{purport}\n")

    if v.get("vedabase_url"):
        parts.append(f"[Read on Vedabase]({v['vedabase_url']})")

    return "\n".join(parts)


@mcp.tool()
async def lookup_verse(reference: str) -> str:
    """Look up a specific Bhagavad Gita verse by reference.

    Accepts formats like "BG 2.47", "2.47", "2:47", "bg 15-7", "Bhagavad Gita 9.34".
    Returns the verse with Sanskrit, transliteration, Prabhupada's translation, synonyms, and purport.
    """
    try:
        chapter, verse = parse_verse_ref(reference)
    except ValueError as e:
        return f"Error: {e}"

    ref = make_ref(chapter, verse)
    conn = init_db()
    try:
        cached = get_verse(conn, ref)

        # If cached and has purport (enriched), return directly
        if cached and cached.get("purport"):
            return _format_verse(cached)

        # Fetch (with vedabase.io enrichment)
        verse_data = await fetch_verse(chapter, verse, enrich=True)
        upsert_verse(conn, verse_data)
        return _format_verse(verse_data)
    finally:
        conn.close()


@mcp.tool()
async def search_verses(query: str, max_results: int = 5) -> str:
    """Search cached Bhagavad Gita verses by keyword.

    Searches across transliteration, translation, and Sanskrit text.
    Requires seed_database to have been run for comprehensive results.
    max_results: 1-10 (default 5).
    """
    max_results = max(1, min(10, max_results))
    conn = init_db()
    try:
        count = verse_count(conn)
        if count == 0:
            return (
                "No verses cached yet. Please run the `seed_database` tool first "
                "to download all 700 Bhagavad Gita verses."
            )

        results = db_search(conn, query, max_results)
        if not results:
            return f"No verses found matching '{query}'."

        parts = [f"**Found {len(results)} result(s) for '{query}':**\n"]
        for r in results:
            transliteration = r.get("transliteration", "")
            if len(transliteration) > 100:
                transliteration = transliteration[:100] + "..."
            translation = r.get("translation", "")
            if len(translation) > 150:
                translation = translation[:150] + "..."
            parts.append(
                f"### {r['ref']}\n"
                f"_{transliteration}_\n"
                f"{translation}\n"
            )

        if count < 700:
            parts.append(
                f"\n_Note: Only {count}/700 verses cached. "
                f"Run `seed_database` for complete results._"
            )

        return "\n".join(parts)
    finally:
        conn.close()


@mcp.tool()
async def fuzzy_match_verse(garbled_sanskrit: str, top_n: int = 3) -> str:
    """Match garbled or phonetic Sanskrit from a transcript to the correct Bhagavad Gita verse.

    Useful for correcting misheard/mistranscribed Sanskrit verse text from audio lectures.
    Requires seed_database to have been run for comprehensive matching.
    top_n: number of results (1-5, default 3).
    """
    top_n = max(1, min(5, top_n))
    conn = init_db()
    try:
        verses = get_all_transliterations(conn)
        if not verses:
            return (
                "No verses cached yet. Please run the `seed_database` tool first "
                "to enable fuzzy matching across all 700 verses."
            )

        matches = fuzzy_match(garbled_sanskrit, verses, top_n=top_n)
        if not matches:
            return f"No matches found for: '{garbled_sanskrit}'"

        parts = [f"**Top {len(matches)} match(es) for:** _{garbled_sanskrit}_\n"]
        for i, m in enumerate(matches):
            parts.append(
                f"{i + 1}. **{m['ref']}** (score: {m['score']:.2f})\n"
                f"   _{m['transliteration']}_"
            )

        # Include full translation for the top match
        top_ref = matches[0]["ref"]
        top_verse = get_verse(conn, top_ref)
        if top_verse and top_verse.get("translation"):
            parts.append(
                f"\n**Top match translation ({top_ref}):**\n{top_verse['translation']}"
            )
        if top_verse and top_verse.get("vedabase_url"):
            parts.append(f"\n[Read on Vedabase]({top_verse['vedabase_url']})")

        return "\n".join(parts)
    finally:
        conn.close()


@mcp.tool()
async def get_chapter_summary(chapter: int) -> str:
    """Get Bhagavad Gita chapter metadata and summary.

    chapter: 1-18.
    """
    if not (1 <= chapter <= 18):
        return f"Error: Chapter must be 1-18, got {chapter}."

    try:
        api_data = await fetch_chapter_api(chapter)
        chapter_data = parse_chapter_api(api_data)

        # Cache it
        conn = init_db()
        try:
            upsert_chapter(conn, chapter_data)
        finally:
            conn.close()

        parts = [
            f"## Chapter {chapter}: {chapter_data.get('name', '')}",
            f"**Transliteration:** {chapter_data.get('name_transliterated', '')}",
            f"**Meaning:** {chapter_data.get('name_meaning', '')}",
            f"**Verses:** {chapter_data.get('verses_count', '')}",
        ]
        if chapter_data.get("summary"):
            parts.append(f"\n**Summary:**\n{chapter_data['summary']}")
        return "\n".join(parts)

    except Exception as e:
        return f"Error fetching chapter {chapter}: {e}"


@mcp.tool()
async def seed_database() -> str:
    """Download all 700 Bhagavad Gita verses into the local cache.

    Uses the vedicscriptures API (fast, no scraping). Vedabase.io enrichment
    happens lazily on individual verse lookups.
    Skips if already seeded (≥700 verses cached). Takes 2-5 minutes.
    """
    conn = init_db()
    try:
        count = verse_count(conn)
        if count >= 700:
            return f"Database already seeded with {count} verses. No action needed."

        seeded = 0
        errors = []
        for ch in range(1, 19):
            for v in range(1, CHAPTER_VERSE_COUNTS[ch - 1] + 1):
                try:
                    verse_data = await fetch_verse(ch, v, enrich=False)
                    upsert_verse(conn, verse_data)
                    seeded += 1
                except Exception as e:
                    errors.append(f"BG {ch}.{v}: {e}")
                    logger.warning("Failed to seed BG %d.%d: %s", ch, v, e)

        result = f"Seeded {seeded} verses into local cache."
        if errors:
            result += f"\n{len(errors)} error(s):\n" + "\n".join(errors[:10])
            if len(errors) > 10:
                result += f"\n... and {len(errors) - 10} more."
        return result
    finally:
        conn.close()
