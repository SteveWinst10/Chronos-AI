import logging
import json
from app.services.llm.llm_client import LLMClient
from app.storage.vector_db import search_similarity
from app.storage.neo4j_graph import neo4j_graph

logger = logging.getLogger(__name__)


async def recall_context(user_query: str, limit: int = 5) -> dict:
    """
    Dual-channel recall engine that merges semantic and relational memories.
    
    1. Generates query vector embedding and searches LanceDB vector space.
    2. Identifies matching entities in the graph based on query and similarity texts.
    3. Traverses Neo4j neighborhood of identified entities.
    4. Combines results into a single context structure.
    """
    llm = LLMClient()

    # Step 1: Semantic Retrieval (LanceDB)
    semantic_results = []
    try:
        query_vector = await llm.get_embedding(user_query)
        raw_matches = search_similarity(collection_name="memories", query_vector=query_vector, limit=limit)
        
        for match in raw_matches:
            metadata_str = match.get("metadata", "{}")
            try:
                metadata = json.loads(metadata_str)
            except Exception:
                metadata = {"raw_text": metadata_str}
            
            semantic_results.append({
                "id": match.get("id"),
                "text": metadata.get("raw_text", ""),
                "conversation_id": metadata.get("conversation_id"),
                "distance": match.get("_distance", 1.0)
            })
    except Exception as e:
        logger.error(f"Semantic recall failed: {e}")
        semantic_results = []

    # Combine text from query and retrieved snippets to scan for entity mentions
    combined_scan_text = user_query.lower() + " " + " ".join([m["text"].lower() for m in semantic_results])

    # Step 2: Relational Retrieval (Neo4j Neighborhood Search)
    relational_results = []
    visited_edges = set()
    
    try:
        all_nodes = neo4j_graph.get_all_nodes()
        identified_entities = []
        
        # Identify which graph entities are mentioned in the query or retrieved context
        for node in all_nodes:
            node_name = node["name"]
            if node_name.lower() in combined_scan_text:
                identified_entities.append(node_name)
                
        # Perform neighborhood traverse for each identified entity
        for entity_name in identified_entities:
            neighborhood = neo4j_graph.get_neighborhood(entity_name)
            for path in neighborhood:
                # Deduplicate edges
                edge_key = (path["source"], path["type"], path["target"])
                if edge_key not in visited_edges:
                    visited_edges.add(edge_key)
                    relational_results.append({
                        "source": path["source"],
                        "source_label": path.get("source_label", "CONCEPT"),
                        "relation": path["type"],
                        "target": path["target"],
                        "target_label": path.get("target_label", "CONCEPT"),
                        "properties": path.get("properties", {})
                    })
    except Exception as e:
        logger.error(f"Relational recall failed: {e}")

    # Step 3: Consolidation
    consolidated_context = {
        "semantic_memories": semantic_results,
        "relational_memories": relational_results
    }
    
    logger.info(
        f"Recalled {len(semantic_results)} semantic blocks and "
        f"{len(relational_results)} relational graph triples."
    )
    
    return consolidated_context
