# Vedabase MCP Server — Technical Specification

**Version:** 0.1.0
**Author:** Sree
**Date:** February 20, 2026
**Status:** Draft

---

## 1. Overview

### 1.1 Purpose

The Vedabase MCP Server provides scripture lookup, keyword search, and fuzzy matching tools for Bhagavad Gita verses via the Model Context Protocol (MCP). It is designed to integrate into an agentic lecture-to-notes pipeline, enabling automated verse verification and correction of garbled Sanskrit from audio transcripts.

### 1.2 Problem Statement

Lecture transcripts (generated via Whisper or manual transcription) contain:
- Phonetically garbled Sanskrit verse references (e.g., `"mā mā evaṁ sa jīva-loka"` instead of BG 15.7)
- Imprecise or missing verse numbers
- Transliteration inconsistencies across speakers and transcribers

Manual correction requires cross-referencing Vedabase.io for each verse — a slow, error-prone process that breaks the automation pipeline.

### 1.3 Solution

An MCP server that exposes 5 tools to any MCP-compatible client (Claude Desktop, Claude API, Claude Code), backed by a local SQLite cache of all 700 Bhagavad Gita verses with 21+ translations.

### 1.4 Scope

| In Scope | Out of Scope (v0.1) |
|----------|---------------------|
| Bhagavad Gita (18 chapters, 700 verses) | Śrīmad-Bhāgavatam (SB) |
| Devanāgarī, transliteration, English translations | Caitanya-caritāmṛta (CC) |
| SQLite local cache | Cloud-hosted vector store |
| stdio + programmatic transports | SSE / HTTP remote transport |
| Fuzzy matching via SequenceMatcher | ML-based semantic matching |

---

## 2. Architecture

### 2.1 System Diagram

```
┌─────────────────────────────────────────────────┐
│                  MCP Clients                     │
│  ┌──────────┐  ┌──────────┐  ┌───────────────┐ │
│  │  Claude   │  │  Claude  │  │ lecture_to_   │ │
│  │  Desktop  │  │  Code    │  │ notes.py      │ │
│  └─────┬────┘  └────┬─────┘  └──────┬────────┘ │
└────────┼────────────┼───────────────┼───────────┘
         │ stdio      │ stdio         │ programmatic
         ▼            ▼               ▼
┌─────────────────────────────────────────────────┐
│              vedabase_mcp/server.py              │
│              (FastMCP, 5 tools)                  │
├────────────┬────────────────┬───────────────────┤
│  db.py     │  fetcher.py    │  fuzzy.py         │
│  SQLite    │  HTTP client   │  Transliteration  │
│  cache     │  (httpx)       │  matcher          │
├────────────┴────────────────┴───────────────────┤
│           ~/.vedabase_mcp/cache.db              │
│           (SQLite WAL mode)                      │
└────────────────────┬────────────────────────────┘
                     │ HTTPS (on cache miss)
                     ▼
         ┌───────────────────────┐
         │ vedicscriptures.      │
         │ github.io             │
         │ (Static JSON API)     │
         └───────────────────────┘
```

### 2.2 Module Responsibilities

| Module | File | Responsibility |
|--------|------|----------------|
| **Server** | `server.py` | MCP tool definitions, request routing, response formatting |
| **Database** | `db.py` | SQLite schema, CRUD operations, search queries, cache management |
| **Fetcher** | `fetcher.py` | HTTP client for vedicscriptures.github.io, verse/chapter parsing, bulk seeding |
| **Fuzzy** | `fuzzy.py` | Sanskrit transliteration normalization, similarity scoring, match ranking |

### 2.3 Data Flow

```
User request ("BG 2.47")
    │
    ▼
server.py: parse reference
    │
    ├──► db.py: check SQLite cache
    │       │
    │       ├── HIT  → format and return
    │       │
    │       └── MISS → fetcher.py: GET vedicscriptures.github.io/slok/2/47
    │                       │
    │                       ├── 200 OK → parse JSON, cache in SQLite, return
    │                       │
    │                       └── Error  → return error message
    │
    ▼
Formatted response → MCP Client
```

---

## 3. Data Model

### 3.1 External API (vedicscriptures.github.io)

**Base URL:** `https://vedicscriptures.github.io`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/slok/{chapter}/{verse}` | GET | Single verse with all translations |
| `/chapter/{chapter}` | GET | Chapter metadata |
| `/chapters` | GET | All 18 chapters metadata |

**Verse response shape:**
```json
{
  "_id": "BG2.47",
  "chapter": 2,
  "verse": 47,
  "slok": "कर्मण्येवाधिकारस्ते...",
  "transliteration": "karmaṇyevādhikāraste...",
  "tej": { "author": "Swami Tejomayananda", "ht": "...", "hc": "..." },
  "gambir": { "author": "Swami Gambirananda", "et": "...", "ec": "..." },
  "sankar": { "author": "Sri Shankaracharya", "et": "...", "sc": "..." },
  ...
}
```

**Key fields per author:**
- `et` — English translation
- `ec` — English commentary
- `ht` — Hindi translation
- `hc` — Hindi commentary
- `sc` — Sanskrit commentary

**Rate limiting:** None (static GitHub Pages). No authentication required.

### 3.2 SQLite Schema

**Database location:** `~/.vedabase_mcp/cache.db` (configurable via `VEDABASE_DB_PATH`)

**Pragma:** `journal_mode=WAL` (concurrent read/write safety)

```sql
CREATE TABLE verses (
    ref              TEXT PRIMARY KEY,    -- "BG 2.47"
    chapter          INTEGER NOT NULL,
    verse            INTEGER NOT NULL,
    devanagari       TEXT,                -- Sanskrit in Devanāgarī script
    transliteration  TEXT,                -- IAST romanization
    translations     TEXT,                -- JSON: { "Author Name": "text", ... }
    synonyms         TEXT,                -- Word-for-word (reserved, currently empty)
    vedabase_url     TEXT,                -- Link to vedabase.io page
    raw_json         TEXT,                -- Full API response for future use
    fetched_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE chapters (
    chapter_number      INTEGER PRIMARY KEY,
    name                TEXT,              -- Sanskrit chapter name
    name_transliterated TEXT,
    name_meaning        TEXT,              -- English meaning
    verses_count        INTEGER,
    summary             TEXT,              -- English summary
    raw_json            TEXT
);

CREATE INDEX idx_verses_chapter ON verses(chapter);
CREATE INDEX idx_verses_transliteration ON verses(transliteration);
```

### 3.3 Bhagavad Gita Dimensions

| Metric | Value |
|--------|-------|
| Total chapters | 18 |
| Total verses | 700 |
| Translations per verse | 21+ (multiple authors) |
| Estimated DB size (seeded) | ~15-25 MB |

---

## 4. Tool Specifications

### 4.1 `lookup_verse`

| Attribute | Value |
|-----------|-------|
| **Purpose** | Fetch a specific verse by reference |
| **Input** | `reference: str` — e.g., `"BG 2.47"`, `"2.47"`, `"BG 9:34"`, `"bg 15.7"` |
| **Output** | Formatted markdown with devanāgarī, transliteration, translation, vedabase link |
| **Cache behavior** | Check SQLite first; on miss, fetch from API and cache |
| **Error cases** | Invalid format → parse error; verse not found → 404 message |

**Reference parsing rules:**
- Prefix `BG`, `GITA`, or `BHAGAVAD GITA` is optional (case-insensitive)
- Separator: `.` or `:` or `-`
- Examples: `"BG 2.47"`, `"2:47"`, `"Bhagavad Gita 9.34"`, `"bg 15-7"`

**Output format:**
```markdown
## BG 2.47

**Sanskrit:**
कर्मण्येवाधिकारस्ते मा फलेषु कदाचन |
मा कर्मफलहेतुर्भूर्मा ते सङ्गोऽस्त्वकर्मणि ||२-४७||

**Transliteration:**
_karmaṇyevādhikāraste mā phaleṣu kadācana..._

**Translation:**
Your right is for action alone, never for the results...

[Read on Vedabase](https://vedabase.io/en/library/bg/2/47/)
```

### 4.2 `search_verses`

| Attribute | Value |
|-----------|-------|
| **Purpose** | Keyword search across all cached verses |
| **Input** | `query: str`, `max_results: int` (1-10, default 5) |
| **Output** | Matching verses with references, transliteration excerpts, translation excerpts |
| **Cache dependency** | Requires `seed_database` to have been run for comprehensive results |
| **Search targets** | `transliteration`, `translations` (JSON), `devanagari` columns via SQL `LIKE` |

**Behavior when cache is empty:** Returns instruction to run `seed_database` first.

### 4.3 `fuzzy_match_verse`

| Attribute | Value |
|-----------|-------|
| **Purpose** | Match garbled/phonetic Sanskrit from transcripts to correct verses |
| **Input** | `garbled_sanskrit: str`, `top_n: int` (1-5, default 3) |
| **Output** | Ranked list of matches with similarity scores, top match includes full translation |
| **Cache dependency** | Requires `seed_database` for comprehensive matching |
| **Algorithm** | See §5 Fuzzy Matching Algorithm |

### 4.4 `get_chapter_summary`

| Attribute | Value |
|-----------|-------|
| **Purpose** | Get chapter metadata and summary |
| **Input** | `chapter: int` (1-18) |
| **Output** | Chapter name (Sanskrit + English), verse count, summary |
| **Cache behavior** | Always fetches fresh from API (chapter data is small) |

### 4.5 `seed_database`

| Attribute | Value |
|-----------|-------|
| **Purpose** | Bulk download all 700 verses into local cache |
| **Input** | None |
| **Output** | Status message with count |
| **Duration** | 2-5 minutes (700 sequential HTTP requests) |
| **Idempotency** | Skips if ≥700 verses already cached (uses `INSERT OR REPLACE`) |
| **Network** | Requires internet access to `vedicscriptures.github.io` |

---

## 5. Fuzzy Matching Algorithm

### 5.1 Problem

Lecture transcripts contain garbled Sanskrit like:
- `"mā mā evaṁ sa jīva-loka jīva-bhūta-sanātana"` (should be BG 15.7: `mamaivāṁśo jīvaloke jīvabhūtaḥ sanātanaḥ`)
- `"man manā bhava mad-bhākto mad-yajī mam namāskuru"` (should be BG 9.34: `manmanā bhava madbhakto madyājī māṁ namaskuru`)

### 5.2 Normalization

Before comparison, both query and candidate are normalized:

```
Input:  "Karmaṇy evādhikāras te"
Step 1: lowercase       → "karmaṇy evādhikāras te"
Step 2: strip diacritics → "karmany evadhikaras te"
Step 3: remove punct     → "karmany evadhikaras te"
Step 4: collapse spaces  → "karmany evadhikaras te"
```

**Diacritic mapping:**

| Diacritic | Normalized | Diacritic | Normalized |
|-----------|------------|-----------|------------|
| ā | a | ṣ | sh |
| ī | i | ś | sh |
| ū | u | ṇ | n |
| ṛ | ri | ṅ | n |
| ṝ | ri | ñ | n |
| ṭ | t | ḍ | d |
| ṁ | m | ṃ | m |
| ḥ | h | | |

### 5.3 Scoring

**Combined score** = 0.6 × `sequence_score` + 0.4 × `keyword_score`

| Component | Method | Range |
|-----------|--------|-------|
| `sequence_score` | `difflib.SequenceMatcher.ratio()` on normalized strings | 0.0 – 1.0 |
| `keyword_score` | Set intersection of 3+ char words / max(query keywords, 1) | 0.0 – 1.0 |

**Threshold:** Minimum score of 0.25 to be included in results.

### 5.4 Limitations

- Works best when ≥3 consecutive Sanskrit words are present
- Cannot match by meaning (semantic search) — only by transliteration similarity
- Performance is O(n) across all 700 verses per query (acceptable for this dataset size)
- May return false positives for very common Sanskrit words (e.g., `"kṛṣṇa"`, `"bhagavān"`)

---

## 6. Configuration

### 6.1 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VEDABASE_DB_PATH` | `~/.vedabase_mcp/cache.db` | SQLite database file path |

### 6.2 Claude Desktop Configuration

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
**Linux:** `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "vedabase": {
      "command": "python",
      "args": ["-m", "vedabase_mcp"]
    }
  }
}
```

**With uv:**
```json
{
  "mcpServers": {
    "vedabase": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/vedabase-mcp", "vedabase-mcp"]
    }
  }
}
```

### 6.3 Claude Code Configuration

```bash
claude mcp add vedabase -- python -m vedabase_mcp
```

---

## 7. Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `mcp[cli]` | ≥1.2.0 | MCP Python SDK (FastMCP) |
| `httpx` | ≥0.25.0 | Async HTTP client for API calls |
| Python | ≥3.10 | Runtime (type hints, match statements) |
| `sqlite3` | stdlib | Local verse cache |
| `difflib` | stdlib | SequenceMatcher for fuzzy matching |

No external database, no API keys, no paid services required.

---

## 8. Integration with Lecture-to-Notes Pipeline

### 8.1 Current Pipeline (without MCP)

```
Audio URL → Whisper → transcript.txt → Claude API → notes.md
```

### 8.2 Enhanced Pipeline (with Vedabase MCP)

```
Audio URL → Whisper → transcript.txt
                          │
                          ▼
                    Claude API + MCP Tools
                          │
                    ┌─────┴──────┐
                    │             │
              fuzzy_match    lookup_verse
              (correct        (fetch full
               garbled         verse data)
               Sanskrit)
                    │             │
                    └─────┬──────┘
                          │
                          ▼
                    Enriched notes.md
                    (correct Sanskrit, translations, vedabase links)
```

### 8.3 Integration Code Pattern

```python
# In lecture_to_notes.py, add MCP client as post-processor:

import re
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def enrich_notes_with_verses(notes_text: str) -> str:
    server = StdioServerParameters(command="python", args=["-m", "vedabase_mcp"])
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 1. Find all verse refs and verify them
            refs = re.findall(r'BG\s+\d+\.\d+', notes_text)
            for ref in set(refs):
                result = await session.call_tool("lookup_verse", {"reference": ref})
                # Append verified translation to notes

            # 2. Find garbled Sanskrit blocks and identify them
            # (heuristic: lines with 5+ Sanskrit-looking words)
            garbled = extract_sanskrit_blocks(notes_text)
            for block in garbled:
                result = await session.call_tool("fuzzy_match_verse", {
                    "garbled_sanskrit": block
                })
                # Replace garbled text with corrected reference

    return enriched_notes
```

---

## 9. Testing Strategy

### 9.1 Unit Tests

| Module | Test Cases |
|--------|------------|
| `fetcher.py` | Reference parsing: `"BG 2.47"`, `"2:47"`, `"bg 15-7"`, invalid inputs |
| `fuzzy.py` | Normalization: diacritics, punctuation, verse numbers |
| `fuzzy.py` | Scoring: known garbled→correct pairs, threshold filtering |
| `db.py` | Schema init, cache/retrieve, search, stats |

### 9.2 Integration Tests

| Test | Description |
|------|-------------|
| Fetch + cache round-trip | Fetch BG 2.47, verify cached, fetch again from cache |
| Seed + search | Seed 1 chapter, search keywords, verify results |
| Fuzzy end-to-end | Seed BG 9, match `"man mana bhava mad bhakto"` → BG 9.34 |

### 9.3 Known Garbled Sanskrit Test Pairs

From the Surrender lecture transcript:

| Garbled (transcript) | Expected Match | Verse |
|----------------------|----------------|-------|
| `man manā bhava mad-bhākto mad-yajī mam namāskuru` | `manmanā bhava madbhakto madyājī māṁ namaskuru` | BG 9.34 |
| `mā mā evaṁ sa jīva-loka jīva-bhūta-sanātana` | `mamaivāṁśo jīvaloke jīvabhūtaḥ sanātanaḥ` | BG 15.7 |
| `kārama-ñeva-dhikāra-ste māpaleṣu-dhikāṣṭhana` | `karmaṇyevādhikāraste mā phaleṣu kadācana` | BG 2.47 |

---

## 10. Roadmap

### v0.2 — SB Support
- Add Śrīmad-Bhāgavatam data source (identify/build API or scrape)
- Extend `parse_verse_ref` for SB format (`"SB 8.1.15"`)
- Expand SQLite schema for multi-scripture support

### v0.3 — Semantic Search
- Add ChromaDB or LanceDB vector store
- Embed translations + purports for semantic search
- Enable queries like `"what does Krishna say about detachment?"`

### v0.4 — Pipeline Integration
- Auto-detect garbled Sanskrit in transcripts (heuristic + LLM classifier)
- Post-processing hook in `lecture_to_notes.py`
- Batch correction mode for full transcripts

### v0.5 — Remote Deployment
- SSE transport for cloud-hosted MCP server
- Multi-user cache with PostgreSQL backend
- Authentication via MCP auth spec

---

## Appendix A: Bhagavad Gita Chapter Verse Counts

| Ch | Name | Verses | Ch | Name | Verses |
|----|------|--------|----|------|--------|
| 1 | Arjuna Viṣāda Yoga | 47 | 10 | Vibhūti Yoga | 42 |
| 2 | Sāṅkhya Yoga | 72 | 11 | Viśvarūpa Darśana Yoga | 55 |
| 3 | Karma Yoga | 43 | 12 | Bhakti Yoga | 20 |
| 4 | Jñāna Karma Sannyāsa Yoga | 42 | 13 | Kṣetra Kṣetrajña Vibhāga Yoga | 35 |
| 5 | Karma Sannyāsa Yoga | 29 | 14 | Guṇatraya Vibhāga Yoga | 27 |
| 6 | Dhyāna Yoga | 47 | 15 | Puruṣottama Yoga | 20 |
| 7 | Jñāna Vijñāna Yoga | 30 | 16 | Daivāsura Sampad Vibhāga Yoga | 24 |
| 8 | Akṣara Brahma Yoga | 28 | 17 | Śraddhātraya Vibhāga Yoga | 28 |
| 9 | Rāja Vidyā Rāja Guhya Yoga | 34 | 18 | Mokṣa Sannyāsa Yoga | 78 |

**Total: 700 verses**

---

## Appendix B: API Response Authors

| Key | Author | Language |
|-----|--------|----------|
| `gambir` | Swami Gambirananda | English |
| `adi` | Swami Adidevananda | English |
| `sankar` | Sri Shankaracharya | English + Sanskrit |
| `tej` | Swami Tejomayananda | Hindi |
| `rpiurp` | Sri Ramanuja | English + Sanskrit |
| `abhinav` | Sri Abhinavagupta | Sanskrit |
| `madhav` | Sri Madhavacharya | Sanskrit |
| `jaya` | Sri Jayatritha | Sanskrit |
| `vallabh` | Sri Vallabhacharya | Sanskrit |
| `ms` | Dr. S. Sankaranarayan | English |
| `spiurp` | Srila Prabhupada | English |
| `neel` | Sri Neelkanth | Sanskrit |
| `puru` | Sri Purushottamji | Hindi |
| `chinmay` | Swami Chinmayananda | Hindi |

---

*End of specification.*