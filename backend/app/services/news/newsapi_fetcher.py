import httpx
from app.core.config import settings

async def fetch_raw_newsapi_articles(query: str = "technology") -> dict:
    """
    Connects to NewsAPI.org and downloads a raw JSON payload of 
    recent news articles based on a search term.
    """
    # 1. The digital address where NewsAPI listens for requests
    url = "https://newsapi.org/v2/everything"
    
    # 2. The parameters we pack into our request (what we want to look for)
    params = {
        "q": query,
        "apiKey": settings.NEWS_API_KEY, # Reuses your secure key automatically!
        "language": "en",
        "pageSize": 10  # Let's pull 10 articles at a time for testing
    }
    
    # 3. Use an async HTTP client to ping the web server
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params)
            
            # If the response code is 200 (Success), pass the raw data back
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Failed to fetch. Status code: {response.status_code}"}
                
        except Exception as e:
            return {"error": f"Network connection failed: {str(e)}"}