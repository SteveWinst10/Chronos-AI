import feedparser

def fetch_raw_rss_feed(feed_url: str = "http://feeds.bbci.co.uk/news/technology/rss.xml") -> list:
    """
    Reads a standard open-source RSS media feed url and extracts 
    the raw article listings.
    """
    try:
        # feedparser handles reading the raw web text format automatically
        feed = feedparser.parse(feed_url)
        
        articles = []
        # Loop through the list of entries found in the RSS feed
        for entry in feed.entries[:10]: # Grab the top 10 breaking items
            articles.append({
                "title": entry.get("title", ""),
                "content": entry.get("summary", ""), # RSS calls text content a 'summary'
                "source": feed_url,
                "link": entry.get("link", "")
            })
            
        return articles
        
    except Exception as e:
        return [{"error": f"Failed parsing RSS link: {str(e)}"}]