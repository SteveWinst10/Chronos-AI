import os
import re
import hashlib
import asyncio
from typing import Optional

from app.storage.cache import cache

# Default TTL (in days) – can be overridden via DUPLICATE_TTL_DAYS env var
DEFAULT_TTL_DAYS = int(os.getenv("DUPLICATE_TTL_DAYS", "30"))

def _normalize_text(text: str) -> str:
    """Normalize text for hashing.

    - Lower‑case
    - Remove punctuation
    - Collapse whitespace
    """
    text = text.lower()
    # Remove any character that is not alphanumeric or whitespace
    text = re.sub(r"[^\w\s]", "", text)
    # Collapse multiple whitespace into a single space
    text = re.sub(r"\s+", " ", text).strip()
    return text

async def _simhash(text: str, bits: int = 128) -> int:
    """Compute a SimHash value for *text*.

    The implementation follows the classic SimHash algorithm:
    1. Tokenise the normalized text.
    2. Hash each token (SHA‑256 → integer).
    3. For each bit position, add +1 if the bit is 1, otherwise -1.
    4. The final hash has bits set where the accumulated value > 0.
    """
    norm = _normalize_text(text)
    if not norm:
        return 0
    v = [0] * bits
    for token in norm.split():
        # Use SHA‑256 for a stable, sufficiently long hash
        token_hash = int(hashlib.sha256(token.encode()).hexdigest(), 16)
        for i in range(bits):
            if token_hash & (1 << i):
                v[i] += 1
            else:
                v[i] -= 1
    # Build the final simhash integer
    sim = 0
    for i in range(bits):
        if v[i] > 0:
            sim |= (1 << i)
    return sim

class Deduplicator:
    """Fuzzy deduplication utility using SimHash and Redis cache.

    Usage example::

        dedup = Deduplicator()
        if await dedup.is_duplicate(article_text):
            # skip processing
            ...
    """

    def __init__(self, ttl_days: Optional[int] = None):
        # TTL in seconds; default is 30 days unless overridden by env
        ttl_days = ttl_days if ttl_days is not None else DEFAULT_TTL_DAYS
        self.ttl_seconds = ttl_days * 24 * 60 * 60

    async def is_duplicate(self, text: str) -> bool:
        """Return ``True`` if *text* has been seen before.

        The method computes the SimHash, looks it up in ``SystemCache``
        (backed by Redis if configured) and stores the hash when it is new.
        """
        sim = await _simhash(text)
        if sim == 0:
            return False
        key = f"dedup:simhash:{sim}"
        existing = await cache.get(key)
        if existing:
            return True
        # Store a sentinel value; we only care that the key exists
        await cache.set(key, "1", ttl=self.ttl_seconds)
        return False

    async def store(self, text: str) -> None:
        """Force‑store *text*'s SimHash in the cache.

        This can be used when a document is processed and you want to ensure
        future duplicates are detected.
        """
        sim = await _simhash(text)
        if sim == 0:
            return
        key = f"dedup:simhash:{sim}"
        await cache.set(key, "1", ttl=self.ttl_seconds)

# Convenience module‑level function for quick checks
async def is_duplicate(text: str) -> bool:
    """Quick‑fire duplicate check without instantiating the class.
    """
    dedup = Deduplicator()
    return await dedup.is_duplicate(text)
