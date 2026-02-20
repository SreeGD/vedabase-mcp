"""Manual standalone test for the Vedabase MCP Server.

Run: python test_manual.py
"""

import asyncio
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    server = StdioServerParameters(
        command=sys.executable,
        args=["-m", "vedabase_mcp"],
    )

    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 1. List available tools
            tools = await session.list_tools()
            print("=== Available Tools ===")
            for t in tools.tools:
                print(f"  - {t.name}: {t.description[:80]}...")
            print()

            # 2. Look up a single verse
            print("=== lookup_verse('BG 2.47') ===")
            result = await session.call_tool("lookup_verse", {"reference": "BG 2.47"})
            print(result.content[0].text[:500])
            print()

            # 3. Get chapter summary
            print("=== get_chapter_summary(2) ===")
            result = await session.call_tool("get_chapter_summary", {"chapter": 2})
            print(result.content[0].text[:500])
            print()

            # 4. Test fuzzy match (needs seeded DB — skip if empty)
            print("=== fuzzy_match_verse (garbled BG 9.34) ===")
            result = await session.call_tool(
                "fuzzy_match_verse",
                {"garbled_sanskrit": "man manā bhava mad-bhākto mad-yajī mam namāskuru"},
            )
            print(result.content[0].text[:500])
            print()

            # 5. Test search (needs seeded DB — skip if empty)
            print("=== search_verses('surrender') ===")
            result = await session.call_tool(
                "search_verses",
                {"query": "surrender"},
            )
            print(result.content[0].text[:500])
            print()

            # 6. Test error handling
            print("=== lookup_verse('invalid') ===")
            result = await session.call_tool("lookup_verse", {"reference": "invalid"})
            print(result.content[0].text)


if __name__ == "__main__":
    asyncio.run(main())
