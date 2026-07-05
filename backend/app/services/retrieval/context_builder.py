"""Deterministic context builder for the Chronos-AI retrieval pipeline.

Sole responsibility: transform a user question and a list of retrieved
MemoryItem objects into a single, ready-to-send LLM prompt string.
"""

from __future__ import annotations

import logging
from typing import Sequence

from app.services.cognee.recall import MemoryItem

logger = logging.getLogger(__name__)

_MAX_CONTEXT_CHARS: int = 48_000
_MAX_CHARS_PER_MEMORY: int = 4_000

_SYSTEM_PREAMBLE = (
    "You are Chronos AI, a news intelligence assistant with persistent memory.\n"
    "You answer questions exclusively from the retrieved news memories shown below.\n"
    "\n"
    "STRICT RULES:\n"
    "1. Answer ONLY using information present in the retrieved memories.\n"
    "2. NEVER hallucinate facts, events, or relationships not found in the memories.\n"
    "3. If the memories do not contain enough information to answer the question,\n"
    "   say so clearly: 'Based on my current memories, I don't have enough information\n"
    "   to answer that question.'\n"
    "4. Always cite your sources. For each claim, mention the article title and\n"
    "   source (e.g. 'According to \"<title>\" via <source>, …').\n"
    "5. Preserve the relevance order of articles — lead with the most relevant.\n"
    "6. Be concise. Do not pad the answer.\n"
)

_MEMORY_HEADER = "RETRIEVED MEMORIES FROM COGNEE:"
_QUESTION_HEADER = "USER QUESTION:"
_INSTRUCTION_FOOTER = (
    "Answer the question using only the memories above. "
    "Be specific, cite sources, and admit if information is insufficient."
)

_NO_MEMORIES_NOTICE = (
    "[NO MEMORIES RETRIEVED]\n"
    "Cognee returned no relevant memories for this question.\n"
    "Inform the user that you currently have no stored information on this topic."
)


def _format_memory_block(index: int, memory: MemoryItem) -> str:
    """Render one MemoryItem as a labelled, human-readable paragraph."""
    score_info = f" (relevance score: {memory.score:.3f})" if memory.score else ""
    title_line = f"[Memory {index}{score_info}]"
    title_text = f"Title   : {memory.title}" if memory.title else "Title   : (untitled)"
    source_text = f"Source  : {memory.source}" if memory.source else "Source  : (unknown)"
    link_text = f"Link    : {memory.link}" if memory.link else "Link    : (no link)"

    content = memory.content or "(no content)"
    if len(content) > _MAX_CHARS_PER_MEMORY:
        content = content[:_MAX_CHARS_PER_MEMORY] + " … [truncated]"

    content_text = f"Content :\n{content}"
    return "\n".join([title_line, title_text, source_text, link_text, content_text])


def _format_memories_section(memories: Sequence[MemoryItem]) -> str:
    """Render all memories into a single section string."""
    if not memories:
        return _NO_MEMORIES_NOTICE

    blocks: list[str] = []
    total_chars = 0

    for idx, memory in enumerate(memories, start=1):
        block = _format_memory_block(idx, memory)
        block_chars = len(block)

        if total_chars + block_chars > _MAX_CONTEXT_CHARS:
            remaining = len(memories) - idx + 1
            blocks.append(f"[… {remaining} additional memories omitted]")
            break

        blocks.append(block)
        total_chars += block_chars

    return ("\n" + "-" * 60 + "\n").join(blocks)


def build_context_prompt(question: str, memories: Sequence[MemoryItem]) -> str:
    """Construct the full LLM prompt from a question and retrieved memories."""
    question_clean = question.strip() if question else "(no question provided)"
    memories_section = _format_memories_section(memories)

    return (
        f"{_MEMORY_HEADER}\n"
        f"{'=' * 60}\n"
        f"{memories_section}\n"
        f"{'=' * 60}\n\n"
        f"{_QUESTION_HEADER}\n"
        f"{question_clean}\n\n"
        f"{_INSTRUCTION_FOOTER}"
    )

def get_system_prompt() -> str:
    """Return the immutable system-level preamble for the LLM."""
    return _SYSTEM_PREAMBLE
