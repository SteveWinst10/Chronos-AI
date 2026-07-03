# app/services/parser/parser.py
import re

def clean_html_content(raw_html: str) -> str:
    """
    Strips HTML tags, sanitizes raw text, and structures 
    the article body cleanly for LLM processing and graph indexing.
    """
    if not raw_html:
        return ""
        
    # 1. Remove script and style elements
    clean_text = re.sub(r'<script[^>]*>([\s\S]*?)</script>', '', raw_html)
    clean_text = re.sub(r'<style[^>]*>([\s\S]*?)</style>', '', clean_text)
    
    # 2. Strip remaining HTML tags
    clean_text = re.sub(r'<[^>]+>', ' ', clean_text)
    
    # 3. Standardize whitespace and remove erratic newlines
    clean_text = re.sub(r'\s+', ' ', clean_text)
    
    return clean_text.strip()

def extract_article_summary(text: str, max_chars: int = 300) -> str:
    """
    Generates a concise preview text constraint from clean strings.
    """
    cleaned = clean_html_content(text)
    if len(cleaned) <= max_chars:
        return cleaned
    return f"{cleaned[:max_chars].rsplit(' ', 1)[0]}..."