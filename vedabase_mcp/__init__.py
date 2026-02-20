"""Vedabase MCP Server — Bhagavad Gita verse lookup, search, and fuzzy matching."""

__version__ = "0.1.0"


def main():
    from vedabase_mcp.server import mcp
    mcp.run()
