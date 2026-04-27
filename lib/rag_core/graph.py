import json
import networkx as nx
from google.cloud import storage

class KnowledgeGraph:
    def __init__(self):
        self.graph = nx.DiGraph()

    def add_triplets(self, triplets: list[dict]) -> None:
        """Add {subject, relation, object} triplets to the graph."""
        for t in triplets:
            if "subject" in t and "relation" in t and "object" in t:
                self.graph.add_edge(t["subject"], t["object"], relation=t["relation"])

    def neighbors(self, entity: str, max_hops: int = 2) -> list[str]:
        """BFS from entity up to max_hops. Returns list of related entity names."""
        if not self.graph.has_node(entity):
            return []

        visited = set([entity])
        queue = [(entity, 0)]
        result = []

        while queue:
            current, hop = queue.pop(0)
            if hop < max_hops:
                # Add successors (directed edges out)
                for neighbor in self.graph.successors(current):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append((neighbor, hop + 1))
                        result.append(neighbor)

                # Add predecessors (directed edges in)
                for neighbor in self.graph.predecessors(current):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append((neighbor, hop + 1))
                        result.append(neighbor)

        return result

    def save_to_gcs(self, bucket_name: str, project_name: str) -> None:
        """Serialize with nx.node_link_data() → JSON → GCS .graphdb/{project}/knowledge_graph.json"""
        data = nx.node_link_data(self.graph)
        serialized = json.dumps(data).encode('utf-8')

        gcs = storage.Client()
        bucket = gcs.bucket(bucket_name)
        blob = bucket.blob(f".graphdb/{project_name}/knowledge_graph.json")
        blob.upload_from_string(serialized, content_type="application/json")

    @classmethod
    def load_from_gcs(cls, bucket_name: str, project_name: str) -> "KnowledgeGraph":
        """Download and deserialize."""
        gcs = storage.Client()
        bucket = gcs.bucket(bucket_name)
        blob = bucket.blob(f".graphdb/{project_name}/knowledge_graph.json")

        kg = cls()
        if blob.exists():
            content = blob.download_as_bytes()
            data = json.loads(content.decode('utf-8'))
            kg.graph = nx.node_link_graph(data)

        return kg

    @property
    def node_count(self) -> int:
        return self.graph.number_of_nodes()