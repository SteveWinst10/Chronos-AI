import logging
import time
from neo4j import GraphDatabase
from app.core.config import settings

logger = logging.getLogger(__name__)


class MockGraphStore:
    """An in-memory fallback graph store for when a live Neo4j instance is not running."""

    def __init__(self):
        self.nodes = {}  # name -> {"label": label, "properties": properties}
        self.edges = []  # list of {"source": s, "target": t, "type": type, "properties": properties}

    def upsert_node(self, name: str, label: str, properties: dict = None):
        if properties is None:
            properties = {}
        # Make a copy of properties so we don't mutate external references
        props = dict(properties)
        props["name"] = name
        
        if name in self.nodes:
            self.nodes[name]["properties"].update(props)
            self.nodes[name]["label"] = label
        else:
            self.nodes[name] = {"label": label, "properties": props}

    def upsert_edge(self, source_name: str, target_name: str, relation: str, properties: dict = None):
        if properties is None:
            properties = {}
        props = dict(properties)
        
        # Ensure source and target nodes exist in mock
        if source_name not in self.nodes:
            self.upsert_node(source_name, "CONCEPT")
        if target_name not in self.nodes:
            self.upsert_node(target_name, "CONCEPT")
            
        # Check if edge already exists
        for edge in self.edges:
            if edge["source"] == source_name and edge["target"] == target_name and edge["type"] == relation:
                edge["properties"].update(props)
                return
                
        self.edges.append({
            "source": source_name,
            "target": target_name,
            "type": relation,
            "properties": props
        })

    def get_neighborhood(self, node_name: str) -> list[dict]:
        neighbors = []
        for edge in self.edges:
            if edge["source"] == node_name:
                target_node = edge["target"]
                target_label = self.nodes.get(target_node, {}).get("label", "CONCEPT")
                neighbors.append({
                    "source": node_name,
                    "target": target_node,
                    "type": edge["type"],
                    "source_label": self.nodes.get(node_name, {}).get("label", "CONCEPT"),
                    "target_label": target_label,
                    "properties": edge["properties"]
                })
            elif edge["target"] == node_name:
                source_node = edge["source"]
                source_label = self.nodes.get(source_node, {}).get("label", "CONCEPT")
                neighbors.append({
                    "source": source_node,
                    "target": node_name,
                    "type": edge["type"],
                    "source_label": source_label,
                    "target_label": self.nodes.get(node_name, {}).get("label", "CONCEPT"),
                    "properties": edge["properties"]
                })
        return neighbors

    def delete_node(self, node_name: str):
        if node_name in self.nodes:
            del self.nodes[node_name]
        self.edges = [e for e in self.edges if e["source"] != node_name and e["target"] != node_name]

    def delete_edge(self, source_name: str, target_name: str, relation: str):
        self.edges = [
            e for e in self.edges 
            if not (e["source"] == source_name and e["target"] == target_name and e["type"] == relation)
        ]

    def get_all_nodes(self) -> list[dict]:
        return [
            {"name": name, "label": data["label"], "properties": data["properties"]}
            for name, data in self.nodes.items()
        ]

    def get_all_edges(self) -> list[dict]:
        return self.edges

    def merge_nodes(self, node_name_a: str, node_name_b: str, label: str):
        """Merge node B into node A."""
        if node_name_b not in self.nodes:
            return
        if node_name_a not in self.nodes:
            self.upsert_node(node_name_a, label)
            
        # Merge properties
        self.nodes[node_name_a]["properties"].update(self.nodes[node_name_b]["properties"])
        
        # Re-route edges
        for edge in self.edges:
            if edge["source"] == node_name_b:
                edge["source"] = node_name_a
            if edge["target"] == node_name_b:
                edge["target"] = node_name_a
                
        # Remove node B
        if node_name_b in self.nodes:
            del self.nodes[node_name_b]

    def get_entity(self, name: str) -> dict:
        node = self.nodes.get(name)
        if not node:
            return None
        return {"name": name, "label": node["label"], "properties": node["properties"]}

    def shortest_path(self, source_name: str, target_name: str) -> list:
        # Simple BFS for mock
        if source_name not in self.nodes or target_name not in self.nodes:
            return []
        
        queue = [[source_name]]
        visited = {source_name}
        
        while queue:
            path = queue.pop(0)
            node = path[-1]
            
            if node == target_name:
                return path
            
            for edge in self.edges:
                neighbor = None
                if edge["source"] == node:
                    neighbor = edge["target"]
                elif edge["target"] == node:
                    neighbor = edge["source"]
                
                if neighbor and neighbor not in visited:
                    visited.add(neighbor)
                    new_path = list(path)
                    new_path.append(neighbor)
                    queue.append(new_path)
        return []

    def entity_degree(self, name: str) -> int:
        degree = 0
        for edge in self.edges:
            if edge["source"] == name or edge["target"] == name:
                degree += 1
        return degree

    def relationship_frequency(self) -> list[dict]:
        freq = {}
        for edge in self.edges:
            rel = edge["type"]
            freq[rel] = freq.get(rel, 0) + 1
        return [{"type": t, "count": c} for t, c in freq.items()]


class Neo4jGraphStore:
    def __init__(self):
        self.driver = None
        self.use_mock = False
        self.mock_store = MockGraphStore()
        
        try:
            # We attempt to connect using the settings Bolt URI
            self.driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
            )
            # Verify connectivity
            self.driver.verify_connectivity()
            logger.info("Successfully connected to Neo4j database.")
        except Exception as e:
            logger.warning(
                f"Could not connect to Neo4j database at {settings.NEO4J_URI}. "
                f"Falling back to in-memory graph store. Error: {e}"
            )
            self.use_mock = True

    def close(self):
        if self.driver:
            self.driver.close()

    def upsert_node(self, name: str, label: str, properties: dict = None):
        if self.use_mock:
            return self.mock_store.upsert_node(name, label, properties)
            
        if properties is None:
            properties = {}
        props = dict(properties)
        props["name"] = name
        
        query = f"""
        MERGE (n:{label} {{name: $name}})
        SET n += $properties
        RETURN n
        """
        try:
            with self.driver.session() as session:
                session.run(query, name=name, properties=props)
        except Exception as e:
            logger.error(f"Neo4j upsert_node failed: {e}. Writing to mock backup store.")
            self.mock_store.upsert_node(name, label, properties)

    def upsert_edge(self, source_name: str, target_name: str, relation: str, properties: dict = None):
        if self.use_mock:
            return self.mock_store.upsert_edge(source_name, target_name, relation, properties)
            
        if properties is None:
            properties = {}
        props = dict(properties)
        
        query = f"""
        MATCH (s {{name: $source_name}})
        MATCH (t {{name: $target_name}})
        MERGE (s)-[r:{relation}]->(t)
        SET r += $properties
        RETURN r
        """
        try:
            with self.driver.session() as session:
                # Ensure start and end nodes exist in Neo4j first
                session.run("MERGE (s:CONCEPT {name: $name})", name=source_name)
                session.run("MERGE (t:CONCEPT {name: $name})", name=target_name)
                session.run(query, source_name=source_name, target_name=target_name, properties=props)
        except Exception as e:
            logger.error(f"Neo4j upsert_edge failed: {e}. Writing to mock backup store.")
            self.mock_store.upsert_edge(source_name, target_name, relation, properties)

    def get_neighborhood(self, node_name: str) -> list[dict]:
        if self.use_mock:
            return self.mock_store.get_neighborhood(node_name)
            
        start_time = time.time()
        query = """
        MATCH (n {name: $node_name})-[r]-(m)
        RETURN n, r, m, type(r) as edge_type, labels(n) as source_labels, labels(m) as target_labels
        """
        try:
            with self.driver.session() as session:
                result = session.run(query, node_name=node_name)
                neighbors = []
                for record in result:
                    n = record["n"]
                    m = record["m"]
                    r = record["r"]
                    edge_type = record["edge_type"]
                    src_labels = record["source_labels"]
                    tgt_labels = record["target_labels"]
                    
                    neighbors.append({
                        "source": n.get("name"),
                        "target": m.get("name"),
                        "type": edge_type,
                        "source_label": src_labels[0] if src_labels else "CONCEPT",
                        "target_label": tgt_labels[0] if tgt_labels else "CONCEPT",
                        "properties": dict(r)
                    })
                
                exec_time = (time.time() - start_time) * 1000
                logger.info(
                    "GraphQuery: get_neighbors(name=%s) — Depth: 1 — Nodes: %d — Edges: %d — Duration: %.2fms",
                    node_name, len(neighbors), len(neighbors), exec_time
                )
                
                return neighbors
        except Exception as e:
            logger.error(f"Neo4j get_neighborhood failed: {e}. Reading from mock backup store.")
            return self.mock_store.get_neighborhood(node_name)

    def delete_node(self, node_name: str):
        if self.use_mock:
            return self.mock_store.delete_node(node_name)
            
        query = """
        MATCH (n {name: $node_name})
        DETACH DELETE n
        """
        try:
            with self.driver.session() as session:
                session.run(query, node_name=node_name)
        except Exception as e:
            logger.error(f"Neo4j delete_node failed: {e}. Performing delete in mock backup store.")
            self.mock_store.delete_node(node_name)

    def delete_edge(self, source_name: str, target_name: str, relation: str):
        if self.use_mock:
            return self.mock_store.delete_edge(source_name, target_name, relation)
            
        query = f"""
        MATCH (s {{name: $source_name}})-[r:{relation}]->(t {{name: $target_name}})
        DELETE r
        """
        try:
            with self.driver.session() as session:
                session.run(query, source_name=source_name, target_name=target_name)
        except Exception as e:
            logger.error(f"Neo4j delete_edge failed: {e}. Performing delete in mock backup store.")
            self.mock_store.delete_edge(source_name, target_name, relation)

    def get_all_nodes(self) -> list[dict]:
        if self.use_mock:
            return self.mock_store.get_all_nodes()
            
        query = """
        MATCH (n)
        RETURN n, labels(n) as labels
        """
        try:
            with self.driver.session() as session:
                result = session.run(query)
                nodes = []
                for record in result:
                    n = record["n"]
                    labels = record["labels"]
                    nodes.append({
                        "name": n.get("name"),
                        "label": labels[0] if labels else "CONCEPT",
                        "properties": dict(n)
                    })
                return nodes
        except Exception as e:
            logger.error(f"Neo4j get_all_nodes failed: {e}. Reading from mock backup store.")
            return self.mock_store.get_all_nodes()

    def get_all_edges(self) -> list[dict]:
        if self.use_mock:
            return self.mock_store.get_all_edges()
            
        query = """
        MATCH (s)-[r]->(t)
        RETURN s.name as source, t.name as target, type(r) as type, properties(r) as properties
        """
        try:
            with self.driver.session() as session:
                result = session.run(query)
                edges = []
                for record in result:
                    edges.append({
                        "source": record["source"],
                        "target": record["target"],
                        "type": record["type"],
                        "properties": dict(record["properties"])
                    })
                return edges
        except Exception as e:
            logger.error(f"Neo4j get_all_edges failed: {e}. Reading from mock backup store.")
            return self.mock_store.get_all_edges()

    def merge_nodes(self, node_name_a: str, node_name_b: str, label: str):
        if self.use_mock:
            return self.mock_store.merge_nodes(node_name_a, node_name_b, label)
            
        try:
            with self.driver.session() as session:
                # Merge node properties
                session.run(
                    f"MATCH (a:{label} {{name: $node_name_a}}) MATCH (b:{label} {{name: $node_name_b}}) SET a += b",
                    node_name_a=node_name_a, node_name_b=node_name_b
                )
                
                # Fetch relationships of node_name_b to recreate them for node_name_a
                rel_query = f"""
                MATCH (b:{label} {{name: $node_name_b}})-[r]-(x)
                RETURN b, r, x, type(r) as type, startNode(r) = b as is_outgoing
                """
                res = session.run(rel_query, node_name_b=node_name_b)
                rels = []
                for record in res:
                    rels.append({
                        "type": record["type"],
                        "target": record["x"].get("name"),
                        "is_outgoing": record["is_outgoing"],
                        "properties": dict(record["r"])
                    })
                
                # Recreate edges for node_name_a
                for rel in rels:
                    if rel["is_outgoing"]:
                        session.run(
                            f"MATCH (a:{label} {{name: $node_name_a}}) MATCH (x {{name: $target}}) "
                            f"MERGE (a)-[r:{rel['type']}]->(x) SET r += $properties",
                            node_name_a=node_name_a, target=rel["target"], properties=rel["properties"]
                        )
                    else:
                        session.run(
                            f"MATCH (a:{label} {{name: $node_name_a}}) MATCH (x {{name: $target}}) "
                            f"MERGE (x)-[r:{rel['type']}]->(a) SET r += $properties",
                            node_name_a=node_name_a, target=rel["target"], properties=rel["properties"]
                        )
                        
                # Detach and delete the duplicate node_name_b
                session.run(
                    f"MATCH (b:{label} {{name: $node_name_b}}) DETACH DELETE b",
                    node_name_b=node_name_b
                )
        except Exception as e:
            logger.error(f"Neo4j merge_nodes failed: {e}. Falling back to mock store merge.")
            self.mock_store.merge_nodes(node_name_a, node_name_b, label)

    def get_entity(self, name: str) -> dict:
        """Fetch a single node by name, following Cognee-style label matching."""
        if self.use_mock:
            return self.mock_store.get_entity(name)
        
        start_time = time.time()
        # Cognee often uses specific labels, but we'll try a generic name match first
        query = "MATCH (n {name: $name}) RETURN n, labels(n) as labels LIMIT 1"
        try:
            with self.driver.session() as session:
                result = session.run(query, name=name)
                record = result.single()
                
                exec_time = (time.time() - start_time) * 1000
                logger.info(
                    "GraphQuery: get_entity(name=%s) — Nodes: %d — Duration: %.2fms",
                    name, 1 if record else 0, exec_time
                )

                if not record:
                    return None
                node = record["n"]
                labels = record["labels"]
                return {
                    "name": node.get("name"),
                    "label": labels[0] if labels else "CONCEPT",
                    "properties": dict(node)
                }
        except Exception as e:
            logger.exception("Neo4j get_entity failed: %s", e)
            return self.mock_store.get_entity(name)

    def get_neighbors(self, node_name: str) -> list[dict]:
        """Alias for get_neighborhood to match Phase 3 spec."""
        return self.get_neighborhood(node_name)

    def shortest_path(self, source_name: str, target_name: str, max_depth: int = 5) -> list[str]:
        """Find the shortest path between two entities by name."""
        if self.use_mock:
            return self.mock_store.shortest_path(source_name, target_name)
        
        query = """
        MATCH (s {name: $source_name}), (t {name: $target_name})
        MATCH p = shortestPath((s)-[*]-(t))
        WHERE length(p) <= $max_depth
        RETURN [n in nodes(p) | n.name] as node_names
        """
        try:
            with self.driver.session() as session:
                result = session.run(query, source_name=source_name, target_name=target_name, max_depth=max_depth)
                record = result.single()
                return record["node_names"] if record else []
        except Exception as e:
            logger.exception("Neo4j shortest_path failed: %s", e)
            return self.mock_store.shortest_path(source_name, target_name)

    def related_entities(self, node_name: str, min_strength: float = 0.0) -> list[dict]:
        """Fetch entities related to the given node, optionally filtered by strength."""
        if self.use_mock:
            # Basic fallback: return all immediate neighbors
            return self.get_neighborhood(node_name)
        
        query = """
        MATCH (n {name: $node_name})-[r]-(m)
        WHERE r.strength >= $min_strength OR r.strength IS NULL
        RETURN m.name as name, type(r) as relationship, r.strength as strength, labels(m) as labels
        ORDER BY r.strength DESC
        """
        try:
            with self.driver.session() as session:
                result = session.run(query, node_name=node_name, min_strength=min_strength)
                return [
                    {
                        "name": record["name"],
                        "relationship": record["relationship"],
                        "strength": record["strength"] or 0.0,
                        "label": record["labels"][0] if record["labels"] else "CONCEPT"
                    }
                    for record in result
                ]
        except Exception as e:
            logger.exception("Neo4j related_entities failed: %s", e)
            return self.mock_store.get_neighborhood(node_name)

    def entity_degree(self, name: str) -> int:
        """Fetch the number of connections for an entity (centrality measure)."""
        if self.use_mock:
            return self.mock_store.entity_degree(name)
        
        query = "MATCH (n {name: $name}) RETURN count{ (n)--() } as degree"
        try:
            with self.driver.session() as session:
                result = session.run(query, name=name)
                record = result.single()
                return record["degree"] if record else 0
        except Exception as e:
            logger.exception("Neo4j entity_degree failed: %s", e)
            return self.mock_store.entity_degree(name)

    def relationship_frequency(self) -> list[dict]:
        """Count occurrences of each relationship type in the graph."""
        if self.use_mock:
            return self.mock_store.relationship_frequency()
        
        query = "MATCH ()-[r]->() RETURN type(r) as type, count(r) as count ORDER BY count DESC"
        try:
            with self.driver.session() as session:
                result = session.run(query)
                return [{"type": r["type"], "count": r["count"]} for r in result]
        except Exception as e:
            logger.exception("Neo4j relationship_frequency failed: %s", e)
            return self.mock_store.relationship_frequency()


# Create single global instance
neo4j_graph = Neo4jGraphStore()


def fetch_graph_network(node_name: str) -> list[dict]:
    """Module-level alias for neo4j_graph.get_neighborhood — used by audit scripts and endpoints."""
    return neo4j_graph.get_neighborhood(node_name)
