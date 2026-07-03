import logging
import json
import re
import uuid
from app.services.llm.llm_client import LLMClient
from app.services.llm.prompts import KNOWLEDGE_EXTRACTION_PROMPT
from app.services.cognee.ontologies import validate_triple
from app.storage.neo4j_graph import neo4j_graph
from app.storage.vector_db import upsert_vector

logger = logging.getLogger(__name__)


def parse_json_triples(text: str) -> list[dict]:
    """Parse JSON triples list from LLM output robustly, handling markdown wrappers."""
    cleaned = text.strip()
    # Strip markdown block formatting if present
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z0-9]*\n", "", cleaned)
        cleaned = re.sub(r"\n```$", "", cleaned)
        cleaned = cleaned.strip()
        
    try:
        data = json.loads(cleaned)
        if isinstance(data, list):
            return data
    except Exception:
        # Attempt to find array brackets in case of conversational prefixes
        match = re.search(r"\[\s*\{.*\}\s*\]", cleaned, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
                if isinstance(data, list):
                    return data
            except Exception:
                pass
    logger.warning(f"Failed to parse LLM triples response: {text}")
    return []


async def remember_context(raw_text: str, conversation_id: str) -> None:
    """
    Ingests unstructured text into the long-term memory network.
    
    1. Calls LLM with KNOWLEDGE_EXTRACTION_PROMPT to extract triples.
    2. Validates extracted triples against ontologies.py and saves valid ones to Neo4j.
    3. Generates vector embeddings for the raw text and saves them to LanceDB.
    """
    llm = LLMClient()

    # Step 1: Call LLM to parse text into standard entity triples
    prompt = f"Unstructured Text to Extract:\n\n{raw_text}"
    llm_output = await llm.get_completion(prompt, KNOWLEDGE_EXTRACTION_PROMPT)
    triples = parse_json_triples(llm_output)

    # Step 2: Validate the output and upsert to Neo4j
    valid_triple_count = 0
    for triple in triples:
        source = triple.get("source")
        source_label = triple.get("source_label")
        relation = triple.get("relation")
        target = triple.get("target")
        target_label = triple.get("target_label")

        if not all([source, source_label, relation, target, target_label]):
            continue

        if validate_triple(source_label, relation, target_label):
            # Upsert nodes and edge in Neo4j
            neo4j_graph.upsert_node(
                name=source, 
                label=source_label.upper(), 
                properties={"conversation_id": conversation_id}
            )
            neo4j_graph.upsert_node(
                name=target, 
                label=target_label.upper(), 
                properties={"conversation_id": conversation_id}
            )
            neo4j_graph.upsert_edge(
                source_name=source, 
                target_name=target, 
                relation=relation.upper(), 
                properties={"conversation_id": conversation_id}
            )
            valid_triple_count += 1
        else:
            logger.warning(
                f"Skipping invalid triple topology: "
                f"({source_label}:{source}) -[{relation}]-> ({target_label}:{target})"
            )

    logger.info(f"Retained {valid_triple_count} of {len(triples)} extracted triples in Neo4j Graph.")

    # Step 3: Calculate dense embedding for the text block and upsert to LanceDB
    try:
        embedding = await llm.get_embedding(raw_text)
        vector_id = str(uuid.uuid4())
        metadata_str = json.dumps({
            "raw_text": raw_text,
            "conversation_id": conversation_id
        })
        upsert_vector(
            collection_name="memories", 
            id=vector_id, 
            vector=embedding, 
            metadata=metadata_str
        )
        logger.info(f"Successfully upserted text embedding to vector DB (ID: {vector_id}).")
    except Exception as e:
        logger.error(f"Failed to upsert text embedding to vector DB: {e}")
        raise e
