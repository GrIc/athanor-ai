from typing import TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from lib.rag_core.store import VectorStore
    from lib.rag_core.graph import KnowledgeGraph

logger = logging.getLogger(__name__)

class HybridSearcher:
    def __init__(self, store: "VectorStore", graph: "KnowledgeGraph",
                 max_hops: int = 2, graph_boost: float = 0.3):
        self.store = store
        self.graph = graph
        self.max_hops = max_hops
        self.graph_boost = graph_boost

    def search(self, query: str, query_embedding: list[float], top_k: int = 8) -> list[dict]:
        """Hybrid search combining vector search and graph traversal."""

        # 1. Run vector search → get top_k results
        vector_results = self.store.search(query_embedding, top_k=top_k)

        if self.graph.node_count == 0:
            return vector_results

        # 2. Extract entity names from query (simple keyword match against graph nodes)
        query_lower = query.lower()
        matched_entities = []
        for node in self.graph.graph.nodes:
            if str(node).lower() in query_lower:
                matched_entities.append(node)

        if not matched_entities:
            return vector_results

        # 3. For each entity found in graph: BFS max_hops hops → collect neighbors
        neighborhood = set()
        for entity in matched_entities:
            neighbors = self.graph.neighbors(entity, max_hops=self.max_hops)
            neighborhood.update(neighbors)
            neighborhood.add(entity) # add seed entity as well

        # Convert neighborhood to lower case for case-insensitive matching
        neighborhood_lower = {str(n).lower() for n in neighborhood}

        # 4. Boost chunks that mention these neighbors
        boosted_results = []
        for result in vector_results:
            result_copy = dict(result)
            text_lower = result_copy["text"].lower()

            # Count how many neighborhood entities are mentioned in the chunk text
            mentions = sum(1 for n in neighborhood_lower if n in text_lower)

            if mentions > 0:
                base_score = result_copy["score"]
                # Apply boost based on number of mentions
                # This is a simplified boost since chunks don't have direct source graph links here yet
                boost = self.graph_boost * min(mentions, 3) / 3.0 # cap at 3 mentions
                result_copy["score"] = base_score * (1 + boost)
                result_copy["graph_boosted"] = True

            boosted_results.append(result_copy)

        # Re-sort by boosted score
        boosted_results.sort(key=lambda x: x["score"], reverse=True)
        return boosted_results[:top_k]