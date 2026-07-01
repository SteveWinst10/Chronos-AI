import logging
import json
import re
from app.services.llm.llm_client import LLMClient
from app.services.llm.prompts import CONTEXT_CONSOLIDATION_PROMPT
from app.storage.neo4j_graph import neo4j_graph

logger = logging.getLogger(__name__)


def parse_json_merges(text: str) -> list[dict]:
    """Parse JSON merge recommendations from LLM output robustly."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z0-9]*\n", "", cleaned)
        cleaned = re.sub(r"\n```$", "", cleaned)
        cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
        if isinstance(data, list):
            return data
    except Exception:
        match = re.search(r"\[\s*\{.*\}\s*\]", cleaned, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
                if isinstance(data, list):
                    return data
            except Exception:
                pass
    logger.warning(f"Failed to parse LLM consolidation response: {text}")
    return []


async def optimize_graph_topology() -> None:
    """
    Scans the graph database for duplicate entities/nodes,
    uses the LLM to resolve them, and merges them.
    """
    llm = LLMClient()

    # Step 1: Retrieve all nodes currently stored in the graph
    try:
        nodes = neo4j_graph.get_all_nodes()
    except Exception as e:
        logger.error(f"Failed to retrieve nodes for graph optimization: {e}")
        return

    if len(nodes) < 2:
        logger.info("Not enough nodes in the graph to perform optimization.")
        return

    # Format the nodes for the LLM to analyze
    nodes_list_str = "\n".join([
        f"- {node['name']} (Label: {node['label']})"
        for node in nodes
    ])

    prompt = (
        f"Analyze the following list of nodes from our knowledge graph and identify "
        f"duplicates, synonyms, or near-identical concepts that should be merged:\n\n"
        f"{nodes_list_str}"
    )

    # Step 2: Call LLM to identify duplicates
    llm_output = await llm.get_completion(prompt, CONTEXT_CONSOLIDATION_PROMPT)
    merges = parse_json_merges(llm_output)

    # Step 3: Execute the merges
    successful_merges = 0
    for merge in merges:
        node_to_keep = merge.get("node_to_keep")
        node_to_merge = merge.get("node_to_merge")
        label = merge.get("label")

        if not all([node_to_keep, node_to_merge, label]):
            continue

        try:
            logger.info(f"Merging duplicate node '{node_to_merge}' into canonical '{node_to_keep}' ({label})")
            neo4j_graph.merge_nodes(node_to_keep, node_to_merge, label)
            successful_merges += 1
        except Exception as e:
            logger.error(f"Failed to merge node '{node_to_merge}' into '{node_to_keep}': {e}")

    logger.info(f"Graph optimization complete. Successfully executed {successful_merges} node merges.")
