# Contributing to Vedabase MCP Server

Thank you for your interest in contributing! This project serves the Gaudiya Vaishnava community by providing scripture tools for AI-powered lecture processing.

## Development Setup

```bash
# Clone the repo
git clone https://github.com/SreeGD/vedabase-mcp.git
cd vedabase-mcp

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate   # macOS/Linux
# .venv\Scripts\activate    # Windows

# Install in editable mode with dev dependencies
pip install -e .
pip install pytest pytest-asyncio

# Run tests to verify setup
python -m pytest tests/ -v
```

## Project Structure

```
vedabase_mcp/
  __init__.py       -- Package entry point
  __main__.py       -- python -m vedabase_mcp
  server.py         -- FastMCP server, 5 tool definitions
  db.py             -- SQLite schema, CRUD, search
  fetcher.py        -- HTTP client (API + vedabase.io scraper)
  fuzzy.py          -- Sanskrit transliteration normalization + matching
tests/
  test_db.py        -- Database operations
  test_fetcher.py   -- Reference parsing, API data extraction
  test_fuzzy.py     -- Normalization, scoring, fuzzy matching
```

## How to Contribute

### Reporting Issues

- Use [GitHub Issues](https://github.com/SreeGD/vedabase-mcp/issues)
- Include: what you expected, what happened, steps to reproduce
- For garbled Sanskrit matching issues, include the input text and expected verse

### Submitting Changes

1. Fork the repo and create a branch from `main`
2. Make your changes
3. Add or update tests for any new functionality
4. Ensure all tests pass: `python -m pytest tests/ -v`
5. Submit a pull request with a clear description

### Good First Issues

- Add more garbled Sanskrit test pairs to `tests/test_fuzzy.py`
- Improve the diacritic normalization mapping in `fuzzy.py`
- Add caching for chapter metadata in `get_chapter_summary`
- Handle verse ranges (e.g., "BG 2.46-47")

### Larger Contributions

- **Srimad-Bhagavatam support** (v0.2) -- new API source, extended reference parser
- **Semantic search** (v0.3) -- vector embeddings for meaning-based verse lookup
- **Improved vedabase.io scraping** -- handle Cloudflare challenges more robustly

## Coding Standards

- Python 3.10+ (type hints, match statements OK)
- Keep dependencies minimal -- stdlib preferred where practical
- All verse content must come from authoritative sources (vedabase.io or the API). Never generate scripture content from LLM training data.
- Functions should be documented with docstrings
- Tests required for new functionality

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run a specific test file
python -m pytest tests/test_fuzzy.py -v

# Interactive testing with MCP Inspector
npx @modelcontextprotocol/inspector python -m vedabase_mcp
```

## Architecture Notes

- **Dual-source design**: vedicscriptures.github.io for fast bulk data, vedabase.io for Prabhupada's authoritative content
- **On-demand enrichment**: `seed_database` uses only the fast API. Vedabase.io scraping happens lazily per verse lookup
- **Graceful fallback**: if vedabase.io scraping fails (Cloudflare), the API's `prabhu` key provides Prabhupada's translation
- **SQLite WAL mode**: safe for concurrent reads during fuzzy matching

## Code of Conduct

Be respectful and constructive. This project serves a spiritual community -- approach contributions with care and sincerity.
