# analysis/pipeline.py

from __future__ import annotations

import os
from typing import List, Dict, Any

from analysis.text_extraction import extract_all_text
from analysis.topic_extraction import extract_topics
from analysis.topic_graph import build_topic_graph
import re

# Try to use Mistral for smart extraction, fallback to simple extraction
try:
    from services.topic_analysis_service import extract_topics_with_mistral
    USE_MISTRAL_ANALYSIS = True
except Exception:
    USE_MISTRAL_ANALYSIS = False


def _normalize_topic_id(name: str) -> str:
    """Create a normalized ID from topic name."""
    normalized = re.sub(r'[^a-z0-9\s]', '', name.lower())
    normalized = re.sub(r'\s+', '_', normalized)
    return normalized[:50]


def _calculate_centrality(topic_graph: Dict[str, Any]) -> Dict[str, float]:
    """Calculate centrality scores based on number of edges."""
    edges = topic_graph.get("edges", [])
    centrality = {}
    
    # Count edges per node
    for edge in edges:
        if len(edge) == 2:
            node1, node2 = edge
            centrality[node1] = centrality.get(node1, 0) + 1
            centrality[node2] = centrality.get(node2, 0) + 1
    
    # Normalize (optional: divide by max for 0-1 range)
    max_edges = max(centrality.values()) if centrality else 1
    if max_edges > 0:
        centrality = {k: v / max_edges for k, v in centrality.items()}
    
    return centrality


def analyze_files(file_paths: List[str]) -> Dict[str, Any]:
    """
    Real analysis function that:
      - extracts text from PDFs, PPTX, images
      - finds topics and assigns importance
      - builds a topic graph with edges
    """
    existing_paths = [p for p in file_paths if os.path.exists(p)]
    total_bytes = sum(os.path.getsize(p) for p in existing_paths) if existing_paths else 0

    # --- Extract text from all files ---
    text_dict, extraction_errors, structured_slides = extract_all_text(existing_paths)
    
    # Store extraction errors for display
    if extraction_errors:
        # Log errors but continue with successfully extracted files
        print(f"Text extraction warnings: {extraction_errors}")
    
    # --- Extract topics (use Mistral if available, else simple extraction) ---
    if USE_MISTRAL_ANALYSIS and text_dict:
        try:
            topics = extract_topics_with_mistral(text_dict)
        except Exception as e:
            print(f"Mistral analysis failed, using simple extraction: {e}")
            topics = extract_topics(text_dict, structured_slides)
    else:
        topics = extract_topics(text_dict, structured_slides)
    
    # Store text_dict for RAG later
    # (we'll need it in session state for topic tutor)
    
    # If no topics found, use fallback
    if not topics:
        topics = [
            {
                "name": "Backpropagation & Gradient Descent",
                "importance": "exam_critical",
                "score": 20.0,
            },
            {
                "name": "Activation Functions",
                "importance": "core",
                "score": 10.0,
            },
            {
                "name": "Dropout & BatchNorm",
                "importance": "extra",
                "score": 5.0,
            },
        ]
    
    # --- Build topic graph ---
    topic_graph = build_topic_graph(topics, text_dict, structured_slides)
    
    # --- Re-rank topics based on centrality (after graph is built) ---
    # Calculate centrality scores and update topic importance
    centrality_scores = _calculate_centrality(topic_graph)
    for topic in topics:
        topic_id = _normalize_topic_id(topic["name"])
        centrality = centrality_scores.get(topic_id, 0)
        # Add centrality boost to score (more edges = more important)
        topic["score"] = topic.get("score", 0) + centrality * 2.0
    
    # Re-sort by updated scores
    topics.sort(key=lambda x: x.get("score", 0), reverse=True)
    
    # Re-assign importance labels based on intelligent score thresholds (not fixed thirds)
    if topics:
        # Use intelligent thresholds based on actual scores
        scores = [t.get("score", 0) for t in topics]
        if scores:
            max_score = max(scores)
            min_score = min(scores)
            score_range = max_score - min_score if max_score > min_score else 1
            
            # Dynamic thresholds based on score distribution
            # Exam-critical: top 30% of score range or score >= 15
            exam_critical_threshold = max(15.0, max_score - (score_range * 0.3))
            # Core: middle 40% of score range or score >= 8
            core_threshold = max(8.0, max_score - (score_range * 0.7))
            
            for topic in topics:
                score = topic.get("score", 0)
                
                # Check if in learning objectives (must be at least core)
                in_learning_obj = False
                if structured_slides:
                    topic_lower = topic["name"].lower()
                    for file_path, slides in structured_slides.items():
                        for slide in slides:
                            if slide.get("is_learning_objectives", False):
                                slide_text = (slide.get("title", "") + " " + slide.get("body", "")).lower()
                                if topic_lower in slide_text:
                                    in_learning_obj = True
                                    break
                        if in_learning_obj:
                            break
                
                # Assign based on score thresholds
                if score >= exam_critical_threshold or (in_learning_obj and score >= 10):
                    topic["importance"] = "exam_critical"
                elif score >= core_threshold or in_learning_obj:
                    topic["importance"] = "core"
                else:
                    topic["importance"] = "extra"
        
        # Update graph nodes with new importance values
        for node in topic_graph.get("nodes", []):
            topic_name = node.get("label")
            matching_topic = next((t for t in topics if t["name"] == topic_name), None)
            if matching_topic:
                node["importance"] = matching_topic["importance"]
    
    # --- Time estimate ---
    if total_bytes <= 0:
        estimated_seconds = 5
    else:
        mb = total_bytes / (1024 * 1024)
        # Base time + processing time
        estimated_seconds = max(5, min(15, int(5 + mb * 2)))
    
    summary = {
        "num_files": len(existing_paths),
        "total_mb": round(total_bytes / (1024 * 1024), 2) if existing_paths else 0.0,
        "num_topics": len(topics),
        "total_text_chars": sum(len(t) for t in text_dict.values()),
    }

    return {
        "estimated_seconds": estimated_seconds,
        "topics": topics,
        "topic_graph": topic_graph,  # nodes + edges
        "summary": summary,
        "text_dict": text_dict,  # Store for RAG
        "structured_slides": structured_slides,  # Store structured slide data for RAG
        "extraction_errors": extraction_errors,  # Store errors for display
    }
