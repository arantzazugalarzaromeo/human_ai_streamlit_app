# analysis/topic_extraction.py
"""
Topic extraction and importance scoring from extracted text.
"""

import re
from typing import List, Dict, Any, Tuple, Optional
from collections import Counter, defaultdict


def _normalize_text(text: str) -> str:
    """Normalize text for processing."""
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def _extract_headings(text: str) -> List[str]:
    """
    Extract potential headings/section titles.
    Looks for lines that are:
    - Short (less than 100 chars)
    - Start with numbers or bullets
    - Are in ALL CAPS or Title Case
    - Appear at start of line
    """
    headings = []
    lines = text.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line or len(line) > 100:
            continue
        
        # Check for numbered/bulleted headings
        if re.match(r'^[\d•\-\*]\s+', line):
            heading = re.sub(r'^[\d•\-\*]\s+', '', line)
            if len(heading) > 3:
                headings.append(heading)
        
        # Check for ALL CAPS headings (likely section titles)
        elif line.isupper() and len(line) > 5 and len(line) < 80:
            headings.append(line)
        
        # Check for Title Case headings
        elif re.match(r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*$', line) and len(line) < 80:
            headings.append(line)
    
    return headings


def _extract_n_grams(text: str, n: int = 2, min_freq: int = 2) -> List[Tuple[str, int]]:
    """
    Extract frequent n-grams (phrases) from text.
    Returns list of (phrase, frequency) tuples.
    """
    # Normalize and tokenize
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    
    # Generate n-grams
    ngrams = []
    for i in range(len(words) - n + 1):
        ngram = ' '.join(words[i:i+n])
        ngrams.append(ngram)
    
    # Count frequencies
    counter = Counter(ngrams)
    
    # Filter by minimum frequency and return sorted
    frequent = [(ngram, count) for ngram, count in counter.items() if count >= min_freq]
    return sorted(frequent, key=lambda x: x[1], reverse=True)


def _score_importance_structured(
    topic: str, 
    structured_slides: Dict[str, List[Dict[str, Any]]],
    text_dict: Dict[str, str]
) -> float:
    """
    Score topic importance using structured slide data.
    Higher weight for:
    - Slide titles/section headings (weight: 10.0)
    - Learning objectives slides (weight: 15.0)
    - Key ideas/summary slides (weight: 12.0)
    - Body text frequency (weight: 1.0)
    """
    topic_lower = topic.lower()
    score = 0.0
    
    # Process structured slides if available
    if structured_slides:
        for file_path, file_slides in structured_slides.items():
            total_slides = len(file_slides) if file_slides else 100
            for slide in file_slides:
                title = slide.get("title", "").lower()
                body = slide.get("body", "").lower()
                is_learning_obj = slide.get("is_learning_objectives", False)
                is_key_ideas = slide.get("is_key_ideas", False)
                
                # Check title (highest weight)
                if topic_lower in title:
                    if is_learning_obj:
                        score += 15.0  # Learning objectives slide title
                    elif is_key_ideas:
                        score += 12.0  # Key ideas slide title
                    else:
                        score += 10.0  # Regular slide title
                
                # Check learning objectives slide body
                if is_learning_obj and topic_lower in body:
                    score += 8.0
                
                # Check key ideas slide body
                if is_key_ideas and topic_lower in body:
                    score += 6.0
                
                # Improvement A: Slide position (early slides or recap)
                slide_idx = slide.get("slide_index", 0)
                
                # Early slides (first 10% or first 3 slides)
                if slide_idx < 3 or slide_idx < total_slides * 0.1:
                    if topic_lower in (title + " " + body):
                        score += 3.0  # Bonus for appearing in intro slides
                
                # Recap/summary slides (last 10% or last 3 slides)
                if slide_idx >= total_slides - 3 or slide_idx >= total_slides * 0.9:
                    if topic_lower in (title + " " + body):
                        score += 3.0  # Bonus for appearing in recap slides
                
                # Count in body text (lower weight)
                body_count = body.count(topic_lower)
                score += body_count * 1.0
    
    # Fallback: count in all text if no structured data
    if not structured_slides:
        all_text = "\n\n".join(text_dict.values()).lower()
        score = all_text.count(topic_lower) * 1.0
    
    return score


def _score_importance(topic: str, text: str, headings: List[str], structured_slides: Dict[str, List[Dict[str, Any]]] = None, text_dict: Dict[str, str] = None) -> Tuple[str, float]:
    """
    Score topic importance.
    Returns (importance_label, score) where:
    - importance_label: "exam_critical", "core", or "extra"
    - score: numeric score for sorting
    """
    # Use structured scoring if available
    if structured_slides and text_dict:
        base_score = _score_importance_structured(topic, structured_slides, text_dict)
    else:
        # Fallback to simple scoring
        topic_lower = topic.lower()
        text_lower = text.lower()
        
        # Count occurrences
        occurrences = text_lower.count(topic_lower)
        
        # Check if it's a heading
        is_heading = any(topic_lower in h.lower() for h in headings)
        
        # Check position (earlier mentions are more important)
        first_pos = text_lower.find(topic_lower)
        position_score = 1.0 if first_pos < len(text) * 0.3 else 0.5
        
        # Calculate base score
        base_score = occurrences * 0.5 + (10 if is_heading else 0) + position_score * 5
    
    # Note: Importance labels will be assigned later based on ranking
    # For now, return a placeholder
    return ("core", base_score)


def extract_topics(text_dict: Dict[str, str], structured_slides: Dict[str, List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """
    Extract topics from all extracted text.
    Returns list of topic dicts with name, importance, and score.
    """
    # Combine all text
    all_text = "\n\n".join(text_dict.values())
    normalized_text = _normalize_text(all_text)
    
    if not normalized_text:
        return []
    
    # Extract headings
    headings = _extract_headings(normalized_text)
    
    # Extract frequent bigrams and trigrams
    bigrams = _extract_n_grams(normalized_text, n=2, min_freq=2)
    trigrams = _extract_n_grams(normalized_text, n=3, min_freq=2)
    
    # Combine candidates
    candidates = []
    
    # Add headings as candidates
    for heading in headings[:20]:  # Limit to top 20 headings
        if len(heading) > 5:
            candidates.append(heading)
    
    # Add frequent phrases
    for phrase, freq in bigrams[:15] + trigrams[:10]:
        # Capitalize first letter of each word
        phrase_title = ' '.join(word.capitalize() for word in phrase.split())
        candidates.append(phrase_title)
    
    # Score and deduplicate
    topic_scores = {}
    for candidate in candidates:
        if len(candidate) < 5 or len(candidate) > 100:
            continue
        
        importance, score = _score_importance(candidate, normalized_text, headings, structured_slides, text_dict)
        
        # Use candidate as key (normalized)
        key = candidate.lower().strip()
        if key not in topic_scores or topic_scores[key][1] < score:
            topic_scores[key] = (candidate, importance, score)
    
    # Convert to list and sort by score
    topics = []
    for name, importance, score in topic_scores.values():
        topics.append({
            "name": name,
            "importance": importance,
            "score": score,
        })
    
    # Sort by score (descending)
    topics.sort(key=lambda x: x["score"], reverse=True)
    
    # Assign importance labels based on ranking (will be re-assigned after centrality)
    # Improvement B: Context-aware thresholds
    # - Topics in learning objectives must be ≥ core
    # - Topics appearing only once in body text → extra
    # - Then use relative thirds for the rest
    
    if topics:
        # First pass: Apply context-aware rules
        for topic in topics:
            topic_lower = topic["name"].lower()
            # Check if topic appears in learning objectives (if we have structured data)
            if structured_slides:
                in_learning_obj = False
                mention_count = 0
                for file_path, slides in structured_slides.items():
                    for slide in slides:
                        slide_text = (slide.get("title", "") + " " + slide.get("body", "")).lower()
                        if topic_lower in slide_text:
                            mention_count += slide_text.count(topic_lower)
                            if slide.get("is_learning_objectives", False):
                                in_learning_obj = True
                
                # Rule: Learning objectives → at least core
                if in_learning_obj and topic["importance"] == "extra":
                    topic["importance"] = "core"
                
                # Rule: Only one mention in body text → extra
                if mention_count <= 1 and topic["score"] < 5.0:
                    topic["importance"] = "extra"
        
        # Second pass: Use intelligent score-based thresholds (fully dynamic, no fixed proportions)
        # Like ChatGPT - analyze the actual distribution and assign based on natural breaks
        scores = [t.get("score", 0) for t in topics]
        if scores:
            sorted_scores = sorted(scores, reverse=True)
            max_score = max(scores)
            min_score = min(scores)
            
            # Find natural breaks in the score distribution (like ChatGPT would)
            # Look for significant gaps between scores to identify importance tiers
            if len(sorted_scores) > 1:
                # Calculate gaps between consecutive scores
                gaps = []
                for i in range(len(sorted_scores) - 1):
                    gap = sorted_scores[i] - sorted_scores[i + 1]
                    gaps.append((i, gap))
                
                # Find the largest gaps (natural break points)
                gaps.sort(key=lambda x: x[1], reverse=True)
                
                # Use largest gap to separate exam-critical from core
                # Use second largest gap to separate core from extra (if exists)
                exam_critical_threshold = sorted_scores[0]  # Start with highest
                core_threshold = min_score  # Start with lowest
                
                if len(gaps) >= 1 and gaps[0][1] > max_score * 0.15:  # Significant gap
                    exam_critical_threshold = sorted_scores[gaps[0][0] + 1]
                if len(gaps) >= 2 and gaps[1][1] > max_score * 0.1:  # Second significant gap
                    core_threshold = sorted_scores[gaps[1][0] + 1]
            else:
                # Single topic - use absolute thresholds
                exam_critical_threshold = 15.0
                core_threshold = 8.0
            
            # Fallback to absolute thresholds if distribution is too uniform
            if max_score - min_score < 5.0:  # Scores are too close together
                exam_critical_threshold = max(15.0, max_score - 2.0)
                core_threshold = max(8.0, max_score - 5.0)
            
            for topic in topics:
                # Only assign if not already set by context-aware rules
                if topic.get("importance") not in ["exam_critical", "core", "extra"]:
                    score = topic.get("score", 0)
                    
                    # Check if in learning objectives
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
                    
                    # Assign based on score thresholds (fully dynamic, no fixed proportions)
                    if score >= exam_critical_threshold or (in_learning_obj and score >= 10):
                        topic["importance"] = "exam_critical"
                    elif score >= core_threshold or in_learning_obj:
                        topic["importance"] = "core"
                    else:
                        topic["importance"] = "extra"
    
    # Return all topics (no fixed limit - let the model decide what's important)
    # The importance labels already filter by actual importance, so we don't need a hard limit
    return topics



