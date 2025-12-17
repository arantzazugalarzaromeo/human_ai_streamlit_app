# analysis/topic_graph.py
"""
Build topic graph with edges based on co-occurrence.
"""

from typing import List, Dict, Any, Tuple, Optional
from collections import defaultdict
import re

# Try to use sentence-transformers for semantic similarity
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    _embedding_model = None
    HAS_EMBEDDINGS = True
except ImportError:
    HAS_EMBEDDINGS = False
    _embedding_model = None


def _get_embedding_model():
    """Get or create embedding model for semantic similarity."""
    global _embedding_model
    if HAS_EMBEDDINGS and _embedding_model is None:
        try:
            _embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception:
            return None
    return _embedding_model


def _calculate_semantic_similarity(text1: str, text2: str) -> float:
    """
    Calculate semantic similarity between two texts using embeddings.
    Returns similarity score between 0 and 1.
    """
    embedding_model = _get_embedding_model()
    if embedding_model is None or not HAS_EMBEDDINGS:
        return 0.0
    
    try:
        embeddings = embedding_model.encode([text1[:500], text2[:500]])
        similarity = np.dot(embeddings[0], embeddings[1]) / (
            np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
        )
        return float(similarity)
    except Exception:
        return 0.0


def _normalize_topic_name(name: str) -> str:
    """Create a normalized ID from topic name."""
    # Convert to lowercase, replace spaces with underscores, remove special chars
    normalized = re.sub(r'[^a-z0-9\s]', '', name.lower())
    normalized = re.sub(r'\s+', '_', normalized)
    return normalized[:50]  # Limit length


def _transitive_reduction(edges: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
    """
    Remove redundant edges using transitive reduction.
    If A -> B and B -> C exist, then A -> C is redundant and removed.
    Returns a list of edges with redundant ones removed.
    """
    if not edges:
        return edges
    
    # Build adjacency list
    graph = defaultdict(list)
    for u, v in edges:
        graph[u].append(v)
    
    # Build set of all edges for quick lookup
    edge_set = set(edges)
    
    # For each edge (u, v), check if there's a path from u to v without using (u, v)
    def has_path_without_edge(start: str, end: str, forbidden_edge: Tuple[str, str]) -> bool:
        """Check if there's a path from start to end without using the forbidden edge."""
        visited = set()
        queue = [start]
        visited.add(start)
        
        while queue:
            node = queue.pop(0)
            for neighbor in graph.get(node, []):
                # Skip the forbidden edge
                if (node, neighbor) == forbidden_edge:
                    continue
                
                if neighbor == end:
                    return True
                
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        
        return False
    
    # Remove redundant edges
    reduced_edges = []
    for edge in edges:
        u, v = edge
        # Check if there's an alternative path from u to v
        if not has_path_without_edge(u, v, edge):
            # No alternative path exists, keep this edge
            reduced_edges.append(edge)
        # If alternative path exists, skip this edge (it's redundant)
    
    return reduced_edges


def build_topic_graph(
    topics: List[Dict[str, Any]], 
    text_dict: Dict[str, str],
    structured_slides: Optional[Dict[str, List[Dict[str, Any]]]] = None
) -> Dict[str, Any]:
    """
    Build a graph structure from topics and text using structured slide data.
    Uses Mistral AI to intelligently determine parent-child relationships (like ChatGPT would).
    Falls back to pattern-based relationships if Mistral is not available.
    Returns dict with 'nodes' and 'edges'.
    """
    # Create nodes
    nodes = []
    topic_to_id = {}
    topic_names = [t["name"] for t in topics]
    
    for topic in topics:
        topic_id = _normalize_topic_name(topic["name"])
        topic_to_id[topic["name"]] = topic_id
        
        nodes.append({
            "id": topic_id,
            "label": topic["name"],
            "importance": topic["importance"],
        })
    
    # Try to use Mistral for intelligent relationship analysis (like ChatGPT)
    mistral_relationships = []
    try:
        from services.concept_map_service import analyze_topic_relationships
        mistral_relationships = analyze_topic_relationships(topics, text_dict, structured_slides)
    except Exception as e:
        print(f"Mistral concept map analysis not available, using pattern-based: {e}")
        mistral_relationships = []
    
    # Build edges based on structured co-occurrence patterns
    edge_strength = defaultdict(float)  # Track edge strength
    directed_edges = set()  # Track explicitly directed edges (parent, child)
    edges_set = set()  # Track unique edges
    
    # Add Mistral-analyzed relationships (these are intelligent parent-child relationships)
    for parent, child in mistral_relationships:
        parent_child = (parent, child)
        directed_edges.add(parent_child)
        if parent_child not in edge_strength:
            edge_strength[parent_child] = 0.0
        edge_strength[parent_child] += 10.0  # Very high weight for Mistral-analyzed relationships
    
    if structured_slides:
        # Process structured slides
        for file_path, slides in structured_slides.items():
            for slide_idx, slide in enumerate(slides):
                title = slide.get("title", "").lower()
                body = slide.get("body", "").lower()
                full_text = (title + " " + body).lower()
                
                # Find topics in this slide
                topics_in_slide = []
                for topic_name in topic_names:
                    topic_lower = topic_name.lower()
                    if topic_lower in full_text:
                        topics_in_slide.append(topic_name)
                
                # Pattern 1: Co-occurrence on same slide (create hierarchy by importance)
                topics_with_importance = []
                for topic_name in topics_in_slide:
                    topic_obj = next((t for t in topics if t["name"] == topic_name), None)
                    if topic_obj:
                        importance_order = {"exam_critical": 3, "core": 2, "extra": 1}
                        topics_with_importance.append((topic_name, importance_order.get(topic_obj["importance"], 1)))
                
                # Sort by importance (highest first)
                topics_with_importance.sort(key=lambda x: x[1], reverse=True)
                
                # Create hierarchical edges: more important topics are parents
                for i, (topic1, imp1) in enumerate(topics_with_importance):
                    for topic2, imp2 in topics_with_importance[i+1:]:
                        if imp1 > imp2:
                            # topic1 is parent of topic2 (directed)
                            parent_child = (topic1, topic2)
                            directed_edges.add(parent_child)
                            if parent_child not in edge_strength:
                                edge_strength[parent_child] = 0.0
                            edge_strength[parent_child] += 3.0
                        elif imp2 > imp1:
                            # topic2 is parent of topic1 (directed)
                            parent_child = (topic2, topic1)
                            directed_edges.add(parent_child)
                            if parent_child not in edge_strength:
                                edge_strength[parent_child] = 0.0
                            edge_strength[parent_child] += 3.0
                        else:
                            # Same importance - use alphabetical order as tiebreaker (undirected, will be sorted)
                            parent_child = tuple(sorted([topic1, topic2]))
                            if parent_child not in edge_strength:
                                edge_strength[parent_child] = 0.0
                            edge_strength[parent_child] += 3.0
                
                # Pattern 2: Bullet relationship (hierarchical - title topic is parent of body topics)
                topics_in_title = [t for t in topics_in_slide if t.lower() in title]
                topics_in_body = [t for t in topics_in_slide if t.lower() in body and t.lower() not in title]
                
                # Create directed parent->child relationships
                for title_topic in topics_in_title:
                    for body_topic in topics_in_body:
                        # Store as (parent, child) tuple for directed edges
                        parent_child = (title_topic, body_topic)
                        directed_edges.add(parent_child)  # Mark as explicitly directed
                        if parent_child not in edge_strength:
                            edge_strength[parent_child] = 0.0
                        edge_strength[parent_child] += 4.0  # Very strong weight for hierarchical relationship
                
                # Pattern 3: Consecutive slides (weaker signal)
                if slide_idx > 0:
                    prev_slide = slides[slide_idx - 1]
                    prev_text = (prev_slide.get("title", "") + " " + prev_slide.get("body", "")).lower()
                    prev_topics = [t for t in topic_names if t.lower() in prev_text]
                    
                    for prev_topic in prev_topics:
                        for curr_topic in topics_in_slide:
                            pair = tuple(sorted([prev_topic, curr_topic]))
                            edge_strength[pair] += 0.5  # Weak weight for consecutive slides
                
                # Improvement A: Semantic similarity as weak signal
                # Check if slides containing different topics are semantically similar
                if HAS_EMBEDDINGS and len(topics_in_slide) >= 1:
                    slide_text = full_text
                    for other_topic in topic_names:
                        if other_topic not in topics_in_slide:
                            # Check if other topic appears in other slides
                            for other_slide_idx, other_slide in enumerate(slides):
                                if other_slide_idx != slide_idx:
                                    other_slide_text = (other_slide.get("title", "") + " " + other_slide.get("body", "")).lower()
                                    if other_topic.lower() in other_slide_text:
                                        # Calculate semantic similarity between slides
                                        similarity = _calculate_semantic_similarity(slide_text[:500], other_slide_text[:500])
                                        if similarity > 0.6:  # Threshold for semantic similarity
                                            for topic_in_slide in topics_in_slide:
                                                pair = tuple(sorted([topic_in_slide, other_topic]))
                                                edge_strength[pair] += similarity * 0.8  # Weak signal (0.5-1.0 range)
                                        break
    else:
        # Fallback: use simple co-occurrence in text
        all_text = "\n\n".join(text_dict.values())
        text_lower = all_text.lower()
        
        # Split into sections (paragraphs or slides separated by double newlines)
        sections = re.split(r'\n\n+', text_lower)
        
        for section in sections:
            topics_in_section = []
            for topic_name in topic_names:
                if topic_name.lower() in section:
                    topics_in_section.append(topic_name)
            
            # Co-occurrence in same section - create hierarchy by importance
            topics_with_importance = []
            for topic_name in topics_in_section:
                topic_obj = next((t for t in topics if t["name"] == topic_name), None)
                if topic_obj:
                    importance_order = {"exam_critical": 3, "core": 2, "extra": 1}
                    topics_with_importance.append((topic_name, importance_order.get(topic_obj["importance"], 1)))
            
            # Sort by importance (highest first)
            topics_with_importance.sort(key=lambda x: x[1], reverse=True)
            
            # Create hierarchical edges: more important topics are parents
            for i, (topic1, imp1) in enumerate(topics_with_importance):
                for topic2, imp2 in topics_with_importance[i+1:]:
                    if imp1 > imp2:
                        # topic1 is parent of topic2 (directed)
                        parent_child = (topic1, topic2)
                        directed_edges.add(parent_child)
                        if parent_child not in edge_strength:
                            edge_strength[parent_child] = 0.0
                        edge_strength[parent_child] += 2.0
                    elif imp2 > imp1:
                        # topic2 is parent of topic1 (directed)
                        parent_child = (topic2, topic1)
                        directed_edges.add(parent_child)
                        if parent_child not in edge_strength:
                            edge_strength[parent_child] = 0.0
                        edge_strength[parent_child] += 2.0
                    else:
                        # Same importance - use alphabetical order as tiebreaker (undirected, will be sorted)
                        parent_child = tuple(sorted([topic1, topic2]))
                        if parent_child not in edge_strength:
                            edge_strength[parent_child] = 0.0
                        edge_strength[parent_child] += 2.0
    
    # Create directed edges based on strength threshold
    # Edges are now directed: (parent, child) representing hierarchical relationships
    edges = []
    directed_edges_set = set()
    
    # Process all relationships (both directed and undirected)
    for pair, strength in edge_strength.items():
        if strength >= 2.0:
            # Check if this is a tuple
            if isinstance(pair, tuple) and len(pair) == 2:
                topic1, topic2 = pair
                
                id1 = topic_to_id.get(topic1)
                id2 = topic_to_id.get(topic2)
                
                if id1 and id2 and id1 != id2:
                    # Check if this is an explicitly directed edge
                    if pair in directed_edges:
                        # Directed pair (parent, child) - keep direction
                        edge_tuple = (id1, id2)
                    else:
                        # Undirected pair - determine direction based on importance
                        topic1_obj = next((t for t in topics if t["name"] == topic1), None)
                        topic2_obj = next((t for t in topics if t["name"] == topic2), None)
                        
                        if topic1_obj and topic2_obj:
                            importance_order = {"exam_critical": 3, "core": 2, "extra": 1}
                            imp1 = importance_order.get(topic1_obj["importance"], 1)
                            imp2 = importance_order.get(topic2_obj["importance"], 1)
                            
                            # Higher importance -> lower importance (parent -> child)
                            if imp1 >= imp2:
                                edge_tuple = (id1, id2)
                            else:
                                edge_tuple = (id2, id1)
                        else:
                            # Fallback: use id order
                            edge_tuple = (id1, id2)
                    
                    if edge_tuple not in directed_edges_set:
                        edges.append(edge_tuple)
                        directed_edges_set.add(edge_tuple)
    
    # Ensure graph connectivity (connect at least some nodes if too sparse)
    if len(edges) < len(topics) // 2:
        # Connect topics by importance hierarchy as fallback
        exam_critical = [t for t in topics if t["importance"] == "exam_critical"]
        core = [t for t in topics if t["importance"] == "core"]
        extra = [t for t in topics if t["importance"] == "extra"]
        
        # Connect exam_critical to core (directed: exam_critical -> core)
        for ec_topic in exam_critical[:min(3, len(exam_critical))]:
            for core_topic in core[:min(2, len(core))]:
                id1 = topic_to_id.get(ec_topic["name"])
                id2 = topic_to_id.get(core_topic["name"])
                if id1 and id2:
                    edge_tuple = (id1, id2)  # Directed: exam_critical -> core
                    if edge_tuple not in directed_edges_set:
                        edges.append(edge_tuple)
                        directed_edges_set.add(edge_tuple)
    
    # Apply transitive reduction: remove redundant edges
    # If A -> B and B -> C, then A -> C is redundant and should be removed
    edges = _transitive_reduction(edges)
    
    return {
        "nodes": nodes,
        "edges": edges,
    }



