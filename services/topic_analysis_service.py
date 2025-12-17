# services/topic_analysis_service.py
"""
Use Mistral to intelligently extract big topics from documents.
"""

import os
from typing import List, Dict, Any

from dotenv import load_dotenv
from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import json
import re

load_dotenv()

_analysis_chain = None


def _build_analysis_chain():
    """Build chain for smart topic extraction."""
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        raise RuntimeError("MISTRAL_API_KEY is not set.")

    llm = ChatMistralAI(
        model="mistral-small-latest",
        temperature=0.2,  # Lower temperature for more consistent extraction
        max_retries=2,
        api_key=api_key,
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                (
                    "You are an expert at analyzing educational materials and identifying "
                    "the KEY topics that students need to focus on for exams.\n"
                    "- Extract only the BIG, MAIN topics (not every small subtopic).\n"
                    "- Focus on major concepts that are important for the exam.\n"
                    "- Like ChatGPT would do - highlight key topics, not every tiny detail.\n"
                    "- For each topic, determine if it's: exam_critical, core, or extra.\n"
                    "- Return a JSON list of topics with name, importance, and brief reason.\n"
                    "- Extract 5-15 main topics maximum. Focus on big concepts."
                ),
            ),
            (
                "human",
                (
                    "Extract the KEY topics from this document text:\n\n"
                    "{document_text}\n\n"
                    "Return ONLY a JSON array like:\n"
                    '[{{"name": "Topic Name", "importance": "exam_critical|core|extra", "reason": "brief reason"}}]\n'
                    "Extract 5-15 main topics maximum. Focus on big concepts, not every small detail. "
                    "Like ChatGPT would do - highlight the key topics students need to know."
                ),
            ),
        ]
    )

    parser = StrOutputParser()
    return prompt | llm | parser


def _get_analysis_chain():
    global _analysis_chain
    if _analysis_chain is None:
        _analysis_chain = _build_analysis_chain()
    return _analysis_chain


def extract_topics_with_mistral(text_dict: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    Use Mistral to intelligently extract big topics.
    Returns list of topics with name, importance, reason, and score.
    """
    # Combine all text (limit to avoid token limits)
    all_text = "\n\n".join(text_dict.values())
    
    # Truncate if too long (keep first 8000 chars for context)
    if len(all_text) > 8000:
        all_text = all_text[:8000] + "\n\n[... text truncated ...]"
    
    if not all_text.strip():
        return []
    
    try:
        chain = _get_analysis_chain()
        response = chain.invoke({"document_text": all_text})
        
        # Try to extract JSON from response
        # Look for JSON array in the response
        json_match = re.search(r'\[.*\]', response, re.DOTALL)
        if json_match:
            topics_json = json.loads(json_match.group())
            
            # Convert to our format
            topics = []
            for i, topic in enumerate(topics_json):
                if isinstance(topic, dict):
                    importance = topic.get("importance", "extra")
                    # Calculate score based on importance
                    score_map = {"exam_critical": 20.0, "core": 10.0, "extra": 5.0}
                    score = score_map.get(importance, 5.0) - (i * 0.5)  # Slight penalty for later topics
                    
                    topics.append({
                        "name": topic.get("name", f"Topic {i+1}"),
                        "importance": importance,
                        "score": score,
                        "reason": topic.get("reason", ""),
                    })
            
            return topics
        else:
            # Fallback: try to parse as plain text
            return []
    except Exception as e:
        print(f"Error in Mistral topic extraction: {e}")
        return []




