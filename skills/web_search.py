"""
skills/web_search.py — Web search skill using DuckDuckGo.

Searches the web for current/real-time information when the user asks
about latest news, events, live data, etc.
"""

from skills.base import BaseSkill


class WebSearchSkill(BaseSkill):
    name = "web_search"
    description = (
        "Search the web for current, real-time, or up-to-date information. "
        "Use this when the user asks about latest news, current events, "
        "weather, sports scores, stock prices, recent releases, or anything "
        "that requires live data you don't have."
    )
    schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query to look up on the web.",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to return. Default: 3.",
            },
        },
        "required": ["query"],
    }

    def __init__(self, max_results: int = 3):
        self._default_max = max_results

    def execute(self, params: dict) -> str:
        query = params.get("query", "")
        if not query:
            return "I need a search query to look things up."

        max_results = params.get("max_results", self._default_max)

        try:
            from ddgs import DDGS

            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))

            if not results:
                return f"No results found for '{query}'."

            # Format results for the LLM to summarise
            lines = [f"Web search results for: '{query}'\n"]
            for i, r in enumerate(results, 1):
                title = r.get("title", "No title")
                body = r.get("body", "No snippet")
                href = r.get("href", "")
                lines.append(f"{i}. {title}")
                lines.append(f"   {body}")
                if href:
                    lines.append(f"   Source: {href}")
                lines.append("")

            return "\n".join(lines).strip()

        except ImportError:
            return "Web search unavailable — 'duckduckgo-search' is not installed."
        except Exception as e:
            return f"Web search failed: {e}"
