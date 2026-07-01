# services/news_pipeline.py
import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("NEWS_API_KEY")

def fetch_raw_news(category="technology"):
    """STEP 1: Fetches the raw JSON data from NewsAPI"""
    url = "https://newsapi.org/v2/top-headlines"
    params = {
        "country": "us",
        "category": category,
        "apiKey": API_KEY
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json().get("articles", [])
    return []

def preprocess_article(raw_article, requested_category="technology"):
    """STEP 2: Cleans, filters, and standardizes a single raw article"""
    # 1. Clean Title
    title = raw_article.get("title", "Untitled Article").strip()
    
    # 2. Clean Description & handle 'None' fallbacks
    description = raw_article.get("description")
    if not description or description.strip() == "":
        description = "No description available."
    else:
        description = description.strip()
        
    # 3. Standardize Date formatting (2026-06-30T00:35:00Z -> 2026-06-30 00:35)
    raw_date = raw_article.get("publishedAt")
    cleaned_date = "Unknown Date"
    if raw_date:
        try:
            parsed_date = datetime.strptime(raw_date.replace("Z", ""), "%Y-%m-%dT%H:%M:%S")
            cleaned_date = parsed_date.strftime("%Y-%m-%d %H:%M")
        except Exception:
            cleaned_date = raw_date 

    # 4. Clean Source and URL
    source = raw_article.get("source", {}).get("name", "Unknown Source").strip()
    url = raw_article.get("url", "").strip()

    # Return the clean schema required by Step 2
    return {
        "title": title,
        "description": description,
        "date": cleaned_date,
        "source": source,
        "category": requested_category.capitalize(),  # Injects 'Technology'
        "url": url
    }

def get_cleaned_news_stream(category="technology"):
    """The main manager function that ties fetching and preprocessing together"""
    raw_articles = fetch_raw_news(category)
    
    cleaned_articles = []
    seen_titles = set()  # Tracks unique articles by their title
    
    for art in raw_articles:
        # Preprocess the article first
        processed = preprocess_article(art, category)
        title_lower = processed["title"].lower().strip()
        
        # Only keep the article if we haven't seen this title yet
        if title_lower not in seen_titles:
            seen_titles.add(title_lower)
            cleaned_articles.append(processed)
            
    return cleaned_articles