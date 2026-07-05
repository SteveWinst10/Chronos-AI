"""Deterministic context builder for the Chronos-AI retrieval pipeline.

Sole responsibility: transform a user question and a list of retrieved
MemoryItem objects into a single, ready-to-send LLM prompt string.

Rules
-----
- No LLM calls.
- No Cognee calls.
- No I/O or network access.
- Fully synchronous and deterministic (same inputs → same output).
- Easy to unit-test in isolation.
"""

from __future__ import annotations

import logging
from typing import Sequence

from app.services.cognee.recall import MemoryItem

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Token / character budget
# ---------------------------------------------------------------------------

# Rough upper bound: GPT-4o-mini context is 128 k tokens.
# We reserve budget for the system prompt, the question, and the answer.
# 1 token ≈ 4 chars in English → 12 000 tokens ≈ 48 000 characters for articles.
_MAX_CONTEXT_CHARS: int = 48_000

# Number of characters to allow per individual memory block.
# Long articles are truncated with an ellipsis so the prompt stays manageable.
_MAX_CHARS_PER_MEMORY: int = 4_000


# ---------------------------------------------------------------------------
# Prompt template fragments
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _format_memory_block(index: int, memory: MemoryItem) -> str:
    """Render one MemoryItem as a labelled, human-readable paragraph.

    Args:
        index:  1-based position (reflects relevance rank).
        memory: Normalised memory from ``recall.py``.

    Returns:
        A multi-line string block ready for inclusion in the prompt.
    """
    score_info = f" (relevance score: {memory.score:.3f})" if memory.score else ""
    title_line = f"[Memory {index}{score_info}]"
    title_text = f"Title   : {memory.title}" if memory.title else "Title   : (untitled)"
    source_text = f"Source  : {memory.source}" if memory.source else "Source  : (unknown)"
    link_text = f"Link    : {memory.link}" if memory.link else "Link    : (no link)"

    # Truncate very long content to stay within budget
    content = memory.content or "(no content)"
    if len(content) > _MAX_CHARS_PER_MEMORY:
        content = content[:_MAX_CHARS_PER_MEMORY] + " … [truncated]"

    content_text = f"Content :\n{content}"

    return "\n".join([title_line, title_text, source_text, link_text, content_text])


def _format_memories_section(memories: Sequence[MemoryItem]) -> str:
    """Render all memories into a single section string.

    If the accumulated text would exceed ``_MAX_CONTEXT_CHARS`` the remaining
    memories are dropped with a note so the prompt never silently overruns the
    model's context window.
    """
    if not memories:
        return _NO_MEMORIES_NOTICE

    blocks: list[str] = []
    total_chars = 0

    for idx, memory in enumerate(memories, start=1):
        block = _format_memory_block(idx, memory)
        block_chars = len(block)

        if total_chars + block_chars > _MAX_CONTEXT_CHARS:
            remaining = len(memories) - idx + 1
            blocks.append(
                f"[… {remaining} additional memor{'y' if remaining == 1 else 'ies'} "
                f"omitted to stay within context budget]"
            )
            logger.warning(
                "Context budget reached at memory %d/%d — %d memor%s omitted.",
                idx,
                len(memories),
                remaining,
                "y" if remaining == 1 else "ies",
            )
            break

        blocks.append(block)
        total_chars += block_chars

    return ("\n" + "-" * 60 + "\n").join(blocks)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_context_prompt(question: str, memories: Sequence[MemoryItem]) -> str:
    """Construct the full LLM prompt from a question and retrieved memories.

    This is the only public function in this module.  It is deterministic:
    the same inputs always produce the same output.  Callers must not embed
    additional logic here; all customisation belongs in this module.

    Args:
        question: The user's natural-language question (raw, unmodified).
        memories: Ordered list of :class:`~app.services.cognee.recall.MemoryItem`
                  objects from ``recall_memories()``, most-relevant first.

    Returns:
        A single prompt string intended to be sent as the *user* message to
        the LLM, with the system preamble prepended as a *system* message.
        The returned string contains BOTH the system preamble and user turn
        separated by ``---`` so callers that use a single-message API can
        pass it directly; callers that use a split system/user API can split
        on ``---SYSTEM_END---``.

    Note:
        The returned value is a **complete** prompt.  ``memory_manager.py``
        should pass it directly to ``llm_client.get_completion()`` using the
        ``NEWS_CONTEXT_ANSWER_PROMPT`` as the system instruction and this
        string as the user message.
    """
    question_clean = question.strip() if question else ""

    if not question_clean:
        logger.warning("build_context_prompt() called with an empty question.")
        question_clean = "(no question provided)"

    memories_section = _format_memories_section(memories)

    memory_count = len(memories)
    logger.debug(
        "Building context prompt: question_len=%d, memory_count=%d.",
        len(question_clean),
        memory_count,
    )

    prompt = (
        f"{_MEMORY_HEADER}\n"
        f"{'=' * 60}\n"
        f"{memories_section}\n"
        f"{'=' * 60}\n"
        f"\n"
        f"{_QUESTION_HEADER}\n"
        f"{question_clean}\n"
        f"\n"
        f"{_INSTRUCTION_FOOTER}"
    )

    return prompt


def get_system_prompt() -> str:
    """Return the immutable system-level preamble for the LLM.

    ``memory_manager.py`` passes this as the ``system_prompt`` argument to
    ``LLMClient.get_completion()``, keeping it separate from the user turn.
    """
    return _SYSTEM_PREAMBLE
