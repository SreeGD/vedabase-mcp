# Vedabase MCP Server

An [MCP](https://modelcontextprotocol.io/) server for Bhagavad Gita verse lookup, keyword search, and fuzzy matching of garbled Sanskrit from lecture transcripts. Built for the Gaudiya Vaishnava community.

Designed to integrate into agentic pipelines (Claude Desktop, Claude Code, or any MCP-compatible client) for automated verse verification and correction of garbled Sanskrit from audio transcripts.

## Features

| Tool | Description |
|------|-------------|
| `lookup_verse` | Fetch any BG verse with Prabhupada's translation, synonyms, and purport |
| `search_verses` | Keyword search across all 700 cached verses |
| `fuzzy_match_verse` | Match garbled/phonetic Sanskrit to correct verses |
| `get_chapter_summary` | Chapter metadata, meaning, and summary |
| `seed_database` | Bulk download all 700 verses into local SQLite cache |

## Data Sources

- **[vedicscriptures.github.io](https://vedicscriptures.github.io/)** -- Static JSON API for Sanskrit text, transliteration, and 22+ translations
- **[vedabase.io](https://vedabase.io/)** -- Srila Prabhupada's Bhaktivedanta translations, word-for-word synonyms, and purports (on-demand scraping)

Prabhupada's translations are the primary/default output. The full API response with all 22 authors is preserved in `raw_json` for future use.

## Quick Start

### Prerequisites

- Python 3.10+
- No API keys or paid services required

### Install

```bash
git clone https://github.com/SreeGD/vedabase-mcp.git
cd vedabase-mcp
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Seed the Database

Download all 700 verses into the local SQLite cache (~2-5 minutes, one-time):

```bash
python -c "
import asyncio
from vedabase_mcp.server import seed_database
print(asyncio.run(seed_database()))
"
```

### Run the Server

```bash
python -m vedabase_mcp
```

### Connect to Claude Desktop

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "vedabase": {
      "command": "/absolute/path/to/vedabase-mcp/.venv/bin/python",
      "args": ["-m", "vedabase_mcp"]
    }
  }
}
```

### Connect to Claude Code

```bash
claude mcp add vedabase -- /absolute/path/to/vedabase-mcp/.venv/bin/python -m vedabase_mcp
```

## Architecture

```
MCP Client (Claude Desktop / Claude Code / custom pipeline)
    |
    | stdio
    v
vedabase_mcp/server.py          -- FastMCP, 5 tools
    |
    +-- db.py                    -- SQLite cache (~/.vedabase_mcp/cache.db)
    +-- fetcher.py               -- HTTP client (vedicscriptures API + vedabase.io scraper)
    +-- fuzzy.py                 -- Sanskrit transliteration normalization + matching
    |
    v (on cache miss)
vedicscriptures.github.io       -- Static JSON API
vedabase.io                     -- Prabhupada's translations (on-demand)
```

## Fuzzy Matching

The server can identify garbled Sanskrit from lecture transcripts:

```
Input:  "man manā bhava mad-bhākto mad-yajī mam namāskuru"
Match:  BG 9.34 -- manmanā bhava madbhakto madyājī māṁ namaskuru (score: 0.82)
```

**How it works:**
1. Normalize both query and candidates (lowercase, strip diacritics, remove punctuation)
2. Combined score = 0.6 x sequence similarity + 0.4 x keyword overlap
3. Return top matches above threshold (0.25)

See the [spec](vedabasemcpspec.md) for the full diacritic mapping table and algorithm details.

## Testing

```bash
pip install pytest pytest-asyncio
python -m pytest tests/ -v
```

### MCP Inspector (interactive testing)

```bash
npx @modelcontextprotocol/inspector python -m vedabase_mcp
```

Opens a web UI at `localhost:6274` where you can call each tool interactively.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `VEDABASE_DB_PATH` | `~/.vedabase_mcp/cache.db` | SQLite database file path |

## Scope

### In Scope (v0.1)

- Bhagavad Gita (18 chapters, 700 verses)
- Devanagari, transliteration, English translations
- SQLite local cache
- stdio transport
- Fuzzy matching via SequenceMatcher

### Roadmap

- **v0.2** -- Srimad-Bhagavatam support
- **v0.3** -- Semantic search (vector embeddings)
- **v0.4** -- Auto-detect garbled Sanskrit in transcripts
- **v0.5** -- SSE/HTTP remote transport, multi-user

See the full [technical specification](vedabasemcpspec.md) for details.

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, coding standards, and how to submit a PR.

## License

[MIT](LICENSE)
