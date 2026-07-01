"""Facade manager for the Chronos-AI Cognee cognitive processing engine."""

from app.services.cognee.remember import remember_context
from app.services.cognee.recall import recall_context
from app.services.cognee.improve import optimize_graph_topology
from app.services.cognee.forget import purge_node_memory


class CogneeMemoryManager:
    """Primary entry point facade class for interacting with the Cognee Engine."""

    @staticmethod
    async def remember_context(raw_text: str, conversation_id: str) -> None:
        """Parse text into graph triples and embeddings and commit to storage."""
        await remember_context(raw_text, conversation_id)

    @staticmethod
    async def recall_context(user_query: str, limit: int = 5) -> dict:
        """Query vector database similarity and retrieve Neo4j graph neighborhoods."""
        return await recall_context(user_query, limit)

    @staticmethod
    async def optimize_graph_topology() -> None:
        """Scan Neo4j graph for duplicates/synonyms, consolidation, and merging."""
        await optimize_graph_topology()

    @staticmethod
    async def purge_node_memory(entity_id: str) -> bool:
        """Evict memory and graph nodes matching a specific entity ID/name."""
        return await purge_node_memory(entity_id)
