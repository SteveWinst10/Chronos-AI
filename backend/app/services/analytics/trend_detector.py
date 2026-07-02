"""TrendDetector: surfaces emerging topics from a rolling article window."""
import logging
from collections import Counter
from typing import Optional

logger = logging.getLogger(__name__)


class TrendDetector:
    """Detects trending topics from a stream of news articles."""

    def __init__(self, window_size: int = 100):
        self._window: list[dict] = []
        self._window_size = window_size

    def ingest(self, article: dict) -> None:
        """Add a preprocessed article to the rolling window."""
        self._window.append(article)
        if len(self._window) > self._window_size:
            self._window.pop(0)

    def top_trends(self, top_n: int = 10) -> list[dict]:
        """Return the top-N trending keywords across the current window."""
        word_counts: Counter = Counter()
        for article in self._window:
            text = f"{article.get('title', '')} {article.get('description', '')}".lower()
            for token in text.split():
                clean = token.strip(".,!?\"'();:-")
                if len(clean) > 3:
                    word_counts[clean] += 1
        return [{"keyword": w, "count": c} for w, c in word_counts.most_common(top_n)]

    def detect(self, articles: Optional[list[dict]] = None, top_n: int = 10) -> list[dict]:
        """Ingest a batch of articles (optional) and return current trends."""
        if articles:
            for a in articles:
                self.ingest(a)
        return self.top_trends(top_n=top_n)
