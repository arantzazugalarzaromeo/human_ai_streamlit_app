# services/concept_map_service.py
"""
Use Mistral to intelligently determine parent-child relationships between topics.
"""

import os
from typing import List, Dict, Any, Tuple, Optional
from dotenv import load_dotenv
from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import json
import re

load_dotenv()

_concept_map_chain = None


def _build_concept_map_chain():
    """Build chain for intelligent topic relationship analysis."""
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        return None  # Return None if API key not available

    llm = ChatMistralAI(
        model="mistral-small-latest",
        temperature=0.2,  # Low temperature for consistent analysis
        max_retries=2,
        api_key=api_key,
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                (
                    "You are an expert at analyzing educational materials and understanding how topics relate to each other. "
                    "Your task is to determine parent-child relationships between topics based on the actual content.\n\n"
                    "**Key principles:**\n"
                    "- A topic is a parent of another topic if the second topic is a subtopic, component, or specific aspect of the first.\n"
                    "- For example: 'Machine Learning' is a parent of 'Neural Networks' because neural networks are a type of machine learning.\n"
                    "- 'Information Retrieval' might be a parent of 'Vector Search' if vector search is a method used in information retrieval.\n"
                    "- Analyze the ACTUAL CONTENT to determine relationships, not just co-occurrence.\n"
                    "- If topics are not clearly related as parent-child, don't force a relationship.\n"
                    "- Return a JSON array of relationships: [{\"parent\": \"Topic A\", \"child\": \"Topic B\", \"reason\": \"brief reason\"}]\n"
                    "- Only include relationships that make sense based on the content.\n"
                ),
            ),
            (
                "human",
                (
                    "Topics:\n{topics_list}\n\n"
                    "Content context:\n{content_context}\n\n"
                    "Analyze these topics and determine parent-child relationships based on the actual content. "
                    "Return ONLY a JSON array of relationships. If topics are not clearly related, don't include them.\n"
                    "Format: [{{\"parent\": \"Topic Name\", \"child\": \"Topic Name\", \"reason\": \"why this is a parent-child relationship\"}}]"
                ),
            ),
        ]
    )

    parser = StrOutputParser()
    return prompt | llm | parser


def _get_concept_map_chain():
    global _concept_map_chain
    if _concept_map_chain is None:
        _concept_map_chain = _build_concept_map_chain()
    return _concept_map_chain


def analyze_topic_relationships(
    topics: List[Dict[str, Any]],
    text_dict: Dict[str, str],
    structured_slides: Optional[Dict[str, List[Dict[str, Any]]]] = None
) -> List[Tuple[str, str]]:
    """
    Use Mistral to intelligently determine parent-child relationships between topics.
    Returns list of (parent, child) tuples.
    """
    chain = _get_concept_map_chain()
    if chain is None:
        return []  # Fallback if Mistral not available
    
    # Prepare topics list
    topics_list = "\n".join([f"- {t.get('name', 'Unknown')}" for t in topics])
    
    # Prepare content context (sample from slides/text)
    content_context = ""
    if structured_slides:
        # Get sample slides for context
        sample_slides = []
        for file_path, slides in structured_slides.items():
            for slide in slides[:5]:  # Sample first 5 slides
                title = slide.get("title", "")
                body = slide.get("body", "")[:500]  # Limit length
                sample_slides.append(f"Title: {title}\nBody: {body[:500]}...")
        content_context = "\n\n".join(sample_slides[:10])  # Max 10 slides
    elif text_dict:
        # Use sample text
        all_text = "\n\n".join(text_dict.values())
        content_context = all_text[:3000]  # First 3000 chars
    
    if not content_context:
        return []
    
    try:
        response = chain.invoke({
            "topics_list": topics_list,
            "content_context": content_context[:5000],  # Limit to avoid token limits
        })
        
        # Extract JSON from response
        json_match = re.search(r'\[.*\]', response, re.DOTALL)
        if json_match:
            relationships_json = json.loads(json_match.group())
            
            # Convert to list of tuples
            relationships = []
            for rel in relationships_json:
                if isinstance(rel, dict) and "parent" in rel and "child" in rel:
                    parent = rel["parent"]
                    child = rel["child"]
                    # Verify both topics exist
                    topic_names = [t.get("name", "") for t in topics]
                    if parent in topic_names and child in topic_names:
                        relationships.append((parent, child))
            
            return relationships
        else:
            return []
    except Exception as e:
        print(f"Error in Mistral concept map analysis: {e}")
        return []


