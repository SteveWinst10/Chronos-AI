"""Ontological definitions and schema validation for graph nodes and edges."""

# Strict, allowable entity node categories (labels)
ALLOWED_NODE_LABELS = {"PERSON", "ORGANIZATION", "CONCEPT", "EVENT"}

# Strict, allowable relationship classifications (types)
ALLOWED_EDGE_TYPES = {"WORKS_FOR", "PART_OF", "OCCURRED_IN"}

# Define specific permitted relational topologies: (source_label, edge_type, target_label)
# This prevents sending invalid connections (e.g., PERSON PART_OF EVENT) to Neo4j.
VALID_TOPOLOGIES = {
    ("PERSON", "WORKS_FOR", "ORGANIZATION"),
    ("ORGANIZATION", "PART_OF", "ORGANIZATION"),
    ("CONCEPT", "PART_OF", "CONCEPT"),
    ("CONCEPT", "PART_OF", "ORGANIZATION"),
    ("EVENT", "OCCURRED_IN", "CONCEPT"),
    ("EVENT", "OCCURRED_IN", "PERSON"),
    ("EVENT", "OCCURRED_IN", "ORGANIZATION"),
    ("EVENT", "OCCURRED_IN", "EVENT"),
    
    # Generic concept mapping if LLM relates concepts/events to people/orgs in standard ways
    ("PERSON", "PART_OF", "ORGANIZATION"),
    ("PERSON", "OCCURRED_IN", "EVENT"),
    ("ORGANIZATION", "OCCURRED_IN", "EVENT"),
}

def validate_triple(source_label: str, edge_type: str, target_label: str) -> bool:
    """
    Validate that a proposed node-edge-node triple conforms to the Cognee ontology.
    
    Returns True if:
      - Both source and target labels are in ALLOWED_NODE_LABELS
      - The edge type is in ALLOWED_EDGE_TYPES
      - (Optional/Topological) The connection configuration matches a valid topology structure
    """
    src = source_label.strip().upper()
    edge = edge_type.strip().upper()
    tgt = target_label.strip().upper()
    
    # First level: basic allowed label checks
    if src not in ALLOWED_NODE_LABELS:
        return False
    if edge not in ALLOWED_EDGE_TYPES:
        return False
    if tgt not in ALLOWED_NODE_LABELS:
        return False
        
    # Second level: topological connectivity verification
    return (src, edge, tgt) in VALID_TOPOLOGIES
