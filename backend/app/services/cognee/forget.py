import logging
from app.storage.neo4j_graph import neo4j_graph
from app.storage.vector_db import get_vector_db

logger = logging.getLogger(__name__)


async def purge_node_memory(entity_id: str) -> bool:
    """
    Cleanly deletes references across both vector_db and neo4j_graph.
    
    - detachment-deletes the entity from Neo4j.
    - evicts any matching vector records in LanceDB memories.
    """
    success = True
    
    # 1. Neo4j Graph cleanup (deletes the node and all connected edges)
    try:
        logger.info(f"Purging entity '{entity_id}' from Neo4j Graph database.")
        neo4j_graph.delete_node(entity_id)
    except Exception as e:
        logger.error(f"Failed to delete entity '{entity_id}' from Neo4j: {e}")
        success = False

    # 2. Vector DB point eviction
    try:
        db = get_vector_db()
        if "memories" in db.table_names():
            table = db.open_table("memories")
            # Try to delete by exact vector ID, or search-and-delete by matching metadata
            logger.info(f"Evicting memories related to '{entity_id}' from Vector DB.")
            
            # Delete by exact ID
            table.delete(f"id = '{entity_id}'")
            # Delete where metadata contains the entity name
            # Escape single quotes in entity name to prevent SQL injection errors
            escaped_id = entity_id.replace("'", "''")
            table.delete(f"metadata LIKE '%{escaped_id}%'")
    except Exception as e:
        logger.error(f"Failed to evict entity '{entity_id}' from Vector DB: {e}")
        success = False

    return success
