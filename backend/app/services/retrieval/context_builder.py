"""Builds structured LLM context from Cognee recall output (semantic + relational memories)."""

from app.core.constants import MAX_RETRIEVAL_RESULTS


def build_context(user_query: str, recall_data: dict) -> str:
    """
    Transform raw recall output into a structured text block
    that can be injected into an LLM system prompt.
    """
    sections = []

    sections.append(f"User Query: {user_query}")

    semantic = recall_data.get("semantic_memories", [])
    if semantic:
        sections.append("\nRelated Memory Snippets:")
        for i, mem in enumerate(semantic[:MAX_RETRIEVAL_RESULTS], 1):
            text = mem.get("text", "").strip()
            if text:
                sections.append(f"  {i}. {text}")

    relational = recall_data.get("relational_memories", [])
    if relational:
        sections.append("\nKnown Entity Relationships:")
        for i, triple in enumerate(relational[:MAX_RETRIEVAL_RESULTS], 1):
            src = triple.get("source", "?")
            rel = triple.get("relation", "?")
            tgt = triple.get("target", "?")
            sections.append(f"  {i}. ({src}) -[{rel}]-> ({tgt})")

    return "\n".join(sections)
