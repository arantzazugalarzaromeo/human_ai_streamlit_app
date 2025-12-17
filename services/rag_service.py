# services/rag_service.py
"""
Enhanced RAG: retrieve relevant text snippets using multiple signals.
Uses direct mentions, semantic similarity, and structural importance.
"""

from typing import List, Dict, Tuple, Optional, Any
import re
from collections import defaultdict

# Try to use sentence-transformers for semantic similarity, fallback to simple approach
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


def _get_topic_synonyms(topic_name: str) -> List[str]:
    """
    Generate related terms/synonyms for a topic.
    Simple keyword-based approach - can be enhanced with embeddings.
    """
    topic_lower = topic_name.lower()
    synonyms = [topic_name]
    
    # Simple synonym mapping for common terms
    synonym_map = {
        "backpropagation": ["gradient descent", "loss derivative", "chain rule", "neural network training"],
        "gradient descent": ["backpropagation", "optimization", "learning rate", "loss function"],
        "activation function": ["sigmoid", "relu", "tanh", "neural activation"],
        "neural network": ["deep learning", "artificial neural network", "ann", "mlp"],
        "overfitting": ["regularization", "generalization", "bias variance"],
        "regularization": ["overfitting", "dropout", "weight decay", "l2"],
    }
    
    # Check if topic matches any key
    for key, related_terms in synonym_map.items():
        if key in topic_lower:
            synonyms.extend(related_terms)
            break
    
    # Also add individual words from the topic
    words = topic_lower.split()
    if len(words) > 1:
        synonyms.extend(words)
    
    return list(set(synonyms))  # Remove duplicates


def _split_into_chunks(text: str, chunk_size: int = 500) -> List[str]:
    """Split text into chunks."""
    chunks = []
    words = text.split()
    
    current_chunk = []
    current_length = 0
    
    for word in words:
        if current_length + len(word) + 1 > chunk_size and current_chunk:
            chunks.append(" ".join(current_chunk))
            current_chunk = [word]
            current_length = len(word)
        else:
            current_chunk.append(word)
            current_length += len(word) + 1
    
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    
    return chunks


def retrieve_relevant_snippets(
    topic_name: str,
    text_dict: Dict[str, str],
    structured_slides: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    max_snippets: int = 5
) -> List[str]:
    """
    Retrieve relevant text snippets using three signals:
    1. Direct mentions (keyword matching)
    2. Semantic similarity (embeddings)
    3. Structural importance (titles, learning objectives, summaries)
    
    Returns list of snippet strings, sorted by combined relevance score.
    """
    # Step 1: Get topic synonyms/related terms
    topic_synonyms = _get_topic_synonyms(topic_name)
    topic_lower = topic_name.lower()
    topic_words = set(topic_lower.split())
    
    # Combine all text
    all_text = "\n\n".join(text_dict.values())
    
    # Split into sentences/chunks
    sentences = re.split(r'[.!?]\s+', all_text)
    # Also split by paragraphs for better chunks
    paragraphs = re.split(r'\n\n+', all_text)
    
    # Combine sentences and paragraphs, preferring paragraphs
    chunks = []
    for para in paragraphs:
        if len(para.strip()) > 50:  # Only meaningful paragraphs
            chunks.append(para.strip())
    # Add sentences that aren't in paragraphs
    for sent in sentences:
        if len(sent.strip()) > 30 and sent.strip() not in all_text[:1000]:  # Avoid duplicates
            chunks.append(sent.strip())
    
    # Score chunks using three signals
    scored_chunks = []
    
    # Get embeddings if available
    embedding_model = _get_embedding_model()
    topic_embedding = None
    if embedding_model and HAS_EMBEDDINGS:
        try:
            topic_embedding = embedding_model.encode([topic_name])[0]
        except Exception:
            topic_embedding = None
    
    for chunk in chunks:
        chunk_lower = chunk.lower()
        score = 0.0
        
        # Signal 1: Direct mentions (highest weight)
        # Check exact phrase match
        if topic_lower in chunk_lower:
            score += 15.0  # Strong signal for direct mention
        
        # Check synonym matches
        for synonym in topic_synonyms:
            if synonym.lower() in chunk_lower and synonym.lower() != topic_lower:
                score += 5.0
        
        # Word overlap
        chunk_words = set(chunk_lower.split())
        overlap = len(topic_words & chunk_words)
        score += overlap * 2.0
        
        # Signal 2: Semantic similarity (if embeddings available)
        if topic_embedding is not None:
            try:
                chunk_embedding = embedding_model.encode([chunk[:500]])[0]  # Limit chunk size
                # Cosine similarity
                similarity = np.dot(topic_embedding, chunk_embedding) / (
                    np.linalg.norm(topic_embedding) * np.linalg.norm(chunk_embedding)
                )
                # Add semantic similarity score (0-1 range, scale to 0-10)
                score += similarity * 10.0
            except Exception:
                pass
        
        # Signal 3: Structural importance
        structural_boost = 0.0
        if structured_slides:
            # Find which slide this chunk comes from
            for file_path, slides in structured_slides.items():
                for slide in slides:
                    slide_text = (slide.get("title", "") + " " + slide.get("body", "")).lower()
                    if chunk_lower[:100] in slide_text or any(word in slide_text for word in chunk_lower.split()[:5]):
                        # Check if in title
                        if chunk_lower[:50] in slide.get("title", "").lower():
                            structural_boost += 8.0  # Title = very important
                        
                        # Check if in learning objectives slide
                        if slide.get("is_learning_objectives", False):
                            structural_boost += 10.0  # Learning objectives = highest
                        
                        # Check if in key ideas/summary slide
                        if slide.get("is_key_ideas", False):
                            structural_boost += 7.0  # Summary = important
                        
                        # Check if in examples (look for keywords)
                        if any(keyword in chunk_lower for keyword in ["example", "for instance", "consider", "suppose"]):
                            structural_boost += 3.0  # Examples = moderately important
                        break
        
        score += structural_boost
        
        if score > 0:
            scored_chunks.append((score, chunk))
    
    # Sort by combined score and take top snippets
    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    
    # Get top snippets
    snippets = []
    seen_texts = set()  # Avoid duplicates
    for score, chunk in scored_chunks[:max_snippets * 2]:  # Get more candidates
        # Normalize chunk for deduplication
        chunk_normalized = chunk.lower().strip()[:100]
        if chunk_normalized not in seen_texts:
            snippets.append(chunk)
            seen_texts.add(chunk_normalized)
            if len(snippets) >= max_snippets:
                break
    
    return snippets


def retrieve_co_occurrence_snippets(
    topic1: str,
    topic2: str,
    text_dict: Dict[str, str],
    max_snippets: int = 3
) -> List[str]:
    """
    Retrieve snippets where both topics appear together.
    """
    all_text = "\n\n".join(text_dict.values())
    sentences = re.split(r'[.!?]\s+', all_text)
    
    topic1_lower = topic1.lower()
    topic2_lower = topic2.lower()
    
    relevant = []
    for sentence in sentences:
        sentence_lower = sentence.lower()
        if topic1_lower in sentence_lower and topic2_lower in sentence_lower:
            relevant.append(sentence.strip())
    
    return relevant[:max_snippets]



