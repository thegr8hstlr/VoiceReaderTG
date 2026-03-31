from __future__ import annotations

import logging

from app.config import settings

logger = logging.getLogger(__name__)


async def search_web(query: str, max_results: int = 5) -> str:
    """Search the web using Tavily (primary) or DuckDuckGo (fallback).

    Returns a formatted string of search results (capped at 15k chars for Retell).
    """
    # Try Tavily first if API key is configured
    if settings.tavily_api_key:
        try:
            return await _search_tavily(query, max_results)
        except Exception:
            logger.exception("Tavily search failed, falling back to DuckDuckGo")

    # Fallback to DuckDuckGo (no API key needed)
    try:
        return _search_duckduckgo(query, max_results)
    except Exception:
        logger.exception("DuckDuckGo search also failed")
        return f"Sorry, I couldn't search the web for '{query}' right now."


async def _search_tavily(query: str, max_results: int) -> str:
    from tavily import AsyncTavilyClient

    client = AsyncTavilyClient(api_key=settings.tavily_api_key)
    response = await client.search(query, max_results=max_results)

    results = []
    for item in response.get("results", []):
        title = item.get("title", "")
        url = item.get("url", "")
        content = item.get("content", "")
        results.append(f"**{title}**\n{url}\n{content}")

    output = f"Web search results for: {query}\n\n" + "\n\n---\n\n".join(results)
    logger.info("Tavily search: %d results for '%s'", len(results), query)
    return output[:15000]


def _search_duckduckgo(query: str, max_results: int) -> str:
    from duckduckgo_search import DDGS

    with DDGS() as ddgs:
        raw_results = list(ddgs.text(query, max_results=max_results))

    results = []
    for item in raw_results:
        title = item.get("title", "")
        url = item.get("href", "")
        body = item.get("body", "")
        results.append(f"**{title}**\n{url}\n{body}")

    output = f"Web search results for: {query}\n\n" + "\n\n---\n\n".join(results)
    logger.info("DuckDuckGo search: %d results for '%s'", len(results), query)
    return output[:15000]
