"""RSS fetcher: wraps the synchronous feedparser in asyncio.to_thread."""
import asyncio
import feedparser


def _parse_feed_sync(feed_url: str) -> list[dict]:
    """Blocking feedparser call - must be run inside asyncio.to_thread."""
    try:
        feed = feedparser.parse(feed_url)
        articles = []
        for entry in feed.entries[:10]:
            articles.append({
                "title": entry.get("title", ""),
                "content": entry.get("summary", ""),
                "source": feed_url,
                "link": entry.get("link", ""),
            })
        return articles
    except Exception as e:
        return [{"error": f"Failed parsing RSS link: {str(e)}"}]


async def fetch_raw_rss_feed(
    feed_url: str = "http://feeds.bbci.co.uk/news/technology/rss.xml",
) -> list[dict]:
    """
    Async-safe RSS fetcher.
    Delegates the blocking feedparser.parse call to a thread pool via
    asyncio.to_thread so the FastAPI event loop is never blocked.
    """
    return await asyncio.to_thread(_parse_feed_sync, feed_url)


def fetch_raw_rss_feed_sync(
    feed_url: str = "http://feeds.bbci.co.uk/news/technology/rss.xml",
) -> list[dict]:
    """Synchronous wrapper for non-async contexts (e.g. news_pipeline)."""
    return _parse_feed_sync(feed_url)
