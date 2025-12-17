# services/evaluation_service.py
"""
Quality Assurance Evaluator Service for AI Tutor.

The evaluator acts as a strict teaching assistant that reviews and perfects
all tutor responses BEFORE they reach the student. It ensures correctness,
appropriate depth, clarity, grounding, and safety.

Role: Like a math teacher reviewing a tutor's explanation before the tutor
presents it to students - fixes errors, improves clarity, ensures completeness.
"""

import json
import os
import re
from typing import Dict, List, Optional, Literal, Tuple

from dotenv import load_dotenv
from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

_evaluator_chains = {}
_revision_chains = {}


def _build_evaluator_chain(evaluation_type: Literal["topic", "edge", "ranking"] = "topic"):
    """Build chain for evaluating tutor responses based on type."""
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        raise RuntimeError("MISTRAL_API_KEY is not set.")

    llm = ChatMistralAI(
        model="mistral-small-latest",
        temperature=0.1,  # Low temperature for consistent, strict evaluation
        max_retries=2,
        api_key=api_key,
    )

    if evaluation_type == "topic":
        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                (
                    "You are a strict, expert teaching assistant reviewing a tutor's explanation "
                    "BEFORE it reaches students. Your job is to identify ALL issues and ensure "
                    "the response is perfect.\n\n"
                    "**Evaluation Rubric (be strict):**\n\n"
                    "a) **Grounding in Materials** (1-5):\n"
                    "   - Uses information from retrieved snippets?\n"
                    "   - Avoids hallucinations (concepts not in slides)?\n"
                    "   - Uses course terminology (same wording as slides)?\n\n"
                    "b) **Depth vs Importance** (1-5):\n"
                    "   - exam_critical: Enough detail (definitions, steps, formulas)?\n"
                    "   - core: Conceptual with key details, not overwhelming?\n"
                    "   - extra: Short and light, no overkill?\n\n"
                    "c) **Clarity & Structure** (1-5):\n"
                    "   - Clear steps/sections?\n"
                    "   - Examples/analogies for abstract topics?\n"
                    "   - Short, understandable sentences?\n\n"
                    "d) **Coverage** (1-5):\n"
                    "   - Covers main slide points?\n"
                    "   - Doesn't miss key points from titles/objectives/summaries?\n\n"
                    "e) **Tone & Cognitive Load** (1-5):\n"
                    "   - Friendly, reassuring, low-anxiety?\n"
                    "   - Appropriate length?\n\n"
                    "f) **Actionability** (1-5):\n"
                    "   - Ends with clear next options?\n\n"
                    "**Global Checks:**\n"
                    "- Grounded in uploaded materials\n"
                    "- No hallucinated formalism\n"
                    "- Consistent with system logic\n"
                    "- Honest about uncertainty\n\n"
                    "**Output:** JSON with scores (1-5) and brief explanations:\n"
                    "{\n"
                    '  "grounding_materials": {"score": 1-5, "explanation": "..."},\n'
                    '  "depth_vs_importance": {"score": 1-5, "explanation": "..."},\n'
                    '  "clarity_structure": {"score": 1-5, "explanation": "..."},\n'
                    '  "coverage_needed": {"score": 1-5, "explanation": "..."},\n'
                    '  "tone_cognitive_load": {"score": 1-5, "explanation": "..."},\n'
                    '  "actionability": {"score": 1-5, "explanation": "..."},\n'
                    '  "needs_revision": true/false,\n'
                    '  "revision_notes": "What needs to be fixed/improved"\n'
                    "}"
                ),
            ),
            (
                "human",
                (
                    "Topic: {topic_name}\n"
                    "Importance: {importance_label}\n"
                    "Question: {user_question}\n"
                    "Context:\n{context_snippets}\n\n"
                    "Tutor's Response:\n{generated_response}\n\n"
                    "Evaluate strictly. If ANY score < 4, set needs_revision=true and explain what to fix."
                ),
            ),
        ])
    
    elif evaluation_type == "edge":
        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                (
                    "You are a strict, expert teaching assistant reviewing a tutor's explanation "
                    "of how two topics connect BEFORE it reaches students.\n\n"
                    "**Evaluation Rubric:**\n\n"
                    "a) **Link Makes Sense** (1-5): Real relationship or vague?\n"
                    "b) **Respects Edge Logic** (1-5): Matches connection type (hierarchical/same slide/consecutive)?\n"
                    "c) **Grounding & Correctness** (1-5): Consistent with slides?\n\n"
                    "**Output:** JSON with scores and revision needs:\n"
                    "{\n"
                    '  "link_makes_sense": {"score": 1-5, "explanation": "..."},\n'
                    '  "respecting_edge_logic": {"score": 1-5, "explanation": "..."},\n'
                    '  "grounding_correctness": {"score": 1-5, "explanation": "..."},\n'
                    '  "needs_revision": true/false,\n'
                    '  "revision_notes": "What needs fixing"\n'
                    "}"
                ),
            ),
            (
                "human",
                (
                    "Topic A: {topic_a}\n"
                    "Topic B: {topic_b}\n"
                    "Edge Signals: {edge_signals}\n"
                    "Context:\n{context_snippets}\n\n"
                    "Tutor's Response:\n{generated_response}\n\n"
                    "Evaluate strictly. If ANY score < 4, set needs_revision=true."
                ),
            ),
        ])
    
    else:  # ranking
        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                (
                    "You are a strict, expert teaching assistant reviewing study priority advice "
                    "BEFORE it reaches students.\n\n"
                    "**Evaluation Rubric:**\n\n"
                    "a) **Respects Ranking** (1-5): Prioritizes exam_critical? Distinguishes levels?\n"
                    "b) **Justification** (1-5): Clear, understandable reasons?\n"
                    "c) **Anxiety-Aware Planning** (1-5): Reasonable plan, not overwhelming?\n\n"
                    "**Output:** JSON with scores and revision needs:\n"
                    "{\n"
                    '  "respects_ranking": {"score": 1-5, "explanation": "..."},\n'
                    '  "justification": {"score": 1-5, "explanation": "..."},\n'
                    '  "anxiety_aware_planning": {"score": 1-5, "explanation": "..."},\n'
                    '  "needs_revision": true/false,\n'
                    '  "revision_notes": "What needs fixing"\n'
                    "}"
                ),
            ),
            (
                "human",
                (
                    "Topics:\n{topic_list}\n"
                    "Question: {user_question}\n\n"
                    "Tutor's Response:\n{generated_response}\n\n"
                    "Evaluate strictly. If ANY score < 4, set needs_revision=true."
                ),
            ),
        ])

    parser = StrOutputParser()
    return prompt | llm | parser


def _build_revision_chain(evaluation_type: Literal["topic", "edge", "ranking"] = "topic"):
    """Build chain for revising/improving tutor responses."""
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        raise RuntimeError("MISTRAL_API_KEY is not set.")

    llm = ChatMistralAI(
        model="mistral-small-latest",
        temperature=0.3,  # Slightly higher for creative improvements
        max_retries=2,
        api_key=api_key,
    )

    if evaluation_type == "topic":
        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                (
                    "You are an expert teaching assistant revising a tutor's explanation to make it perfect. "
                    "Fix ALL issues identified by the evaluator. Maintain the friendly, student-friendly tone "
                    "but ensure correctness, appropriate depth, clarity, and completeness.\n\n"
                    "**Revision Guidelines:**\n"
                    "- Fix any inaccuracies or hallucinations\n"
                    "- Adjust depth to match importance level (exam_critical/core/extra)\n"
                    "- Improve clarity and structure\n"
                    "- Ensure all key points from slides are covered\n"
                    "- Maintain friendly, reassuring tone\n"
                    "- Add clear next steps/actionability\n"
                    "- Use course terminology from slides\n"
                    "- Be honest about uncertainty if slides are limited\n\n"
                    "Return ONLY the revised, perfected response. No meta-commentary."
                ),
            ),
            (
                "human",
                (
                    "Topic: {topic_name}\n"
                    "Importance: {importance_label}\n"
                    "Question: {user_question}\n"
                    "Context:\n{context_snippets}\n\n"
                    "Original Response:\n{original_response}\n\n"
                    "Issues to Fix:\n{revision_notes}\n\n"
                    "Provide the perfected response:"
                ),
            ),
        ])
    
    elif evaluation_type == "edge":
        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                (
                    "You are an expert teaching assistant revising an explanation of how two topics connect. "
                    "Fix ALL issues. Ensure the connection is clear, accurate, and matches the edge type."
                ),
            ),
            (
                "human",
                (
                    "Topic A: {topic_a}\n"
                    "Topic B: {topic_b}\n"
                    "Edge Signals: {edge_signals}\n"
                    "Context:\n{context_snippets}\n\n"
                    "Original Response:\n{original_response}\n\n"
                    "Issues to Fix:\n{revision_notes}\n\n"
                    "Provide the perfected response:"
                ),
            ),
        ])
    
    else:  # ranking
        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                (
                    "You are an expert teaching assistant revising study priority advice. "
                    "Fix ALL issues. Ensure it respects rankings, provides clear justifications, "
                    "and gives anxiety-aware, balanced study plans."
                ),
            ),
            (
                "human",
                (
                    "Topics:\n{topic_list}\n"
                    "Question: {user_question}\n\n"
                    "Original Response:\n{original_response}\n\n"
                    "Issues to Fix:\n{revision_notes}\n\n"
                    "Provide the perfected response:"
                ),
            ),
        ])

    parser = StrOutputParser()
    return prompt | llm | parser


def _get_evaluator_chain(evaluation_type: Literal["topic", "edge", "ranking"] = "topic"):
    """Get or create the evaluator chain."""
    key = f"eval_{evaluation_type}"
    if key not in _evaluator_chains:
        _evaluator_chains[key] = _build_evaluator_chain(evaluation_type)
    return _evaluator_chains[key]


def _get_revision_chain(evaluation_type: Literal["topic", "edge", "ranking"] = "topic"):
    """Get or create the revision chain."""
    key = f"rev_{evaluation_type}"
    if key not in _revision_chains:
        _revision_chains[key] = _build_revision_chain(evaluation_type)
    return _revision_chains[key]


def _parse_json_response(text: str) -> Dict:
    """Parse JSON from LLM response."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        return {}


def evaluate_and_revise_topic_response(
    topic_name: str,
    importance_label: str,
    user_question: str,
    generated_response: str,
    context_snippets: Optional[List[str]] = None,
) -> str:
    """
    Evaluate a topic response and revise it if needed.
    Returns the perfected response (student never sees evaluation).
    """
    eval_chain = _get_evaluator_chain("topic")
    
    context_text = "None provided"
    if context_snippets:
        context_text = "\n".join([f"- {snippet[:200]}..." for snippet in context_snippets[:5]])
    
    # Step 1: Evaluate
    eval_text = eval_chain.invoke({
        "topic_name": topic_name,
        "importance_label": importance_label,
        "user_question": user_question,
        "context_snippets": context_text,
        "generated_response": generated_response,
    })
    
    evaluation = _parse_json_response(eval_text)
    
    # Step 2: Check if revision needed
    needs_revision = evaluation.get("needs_revision", False)
    
    # Also check if any score < 4
    if not needs_revision:
        for key, value in evaluation.items():
            if key not in ["needs_revision", "revision_notes"] and isinstance(value, dict):
                score = value.get("score")
                if score is not None and score < 4:
                    needs_revision = True
                    break
    
    # Step 3: Revise if needed
    if needs_revision:
        revision_notes = evaluation.get("revision_notes", "Improve clarity, correctness, and completeness.")
        rev_chain = _get_revision_chain("topic")
        
        perfected_response = rev_chain.invoke({
            "topic_name": topic_name,
            "importance_label": importance_label,
            "user_question": user_question,
            "context_snippets": context_text,
            "original_response": generated_response,
            "revision_notes": revision_notes,
        })
        return perfected_response.strip()
    
    # Response is good, return as-is
    return generated_response


def evaluate_and_revise_edge_response(
    topic_a: str,
    topic_b: str,
    edge_signals: str,
    generated_response: str,
    context_snippets: Optional[List[str]] = None,
) -> str:
    """Evaluate and revise edge explanation. Returns perfected response."""
    eval_chain = _get_evaluator_chain("edge")
    
    context_text = "None provided"
    if context_snippets:
        context_text = "\n".join([f"- {snippet[:200]}..." for snippet in context_snippets[:5]])
    
    eval_text = eval_chain.invoke({
        "topic_a": topic_a,
        "topic_b": topic_b,
        "edge_signals": edge_signals,
        "context_snippets": context_text,
        "generated_response": generated_response,
    })
    
    evaluation = _parse_json_response(eval_text)
    needs_revision = evaluation.get("needs_revision", False)
    
    if not needs_revision:
        for key, value in evaluation.items():
            if key not in ["needs_revision", "revision_notes"] and isinstance(value, dict):
                score = value.get("score")
                if score is not None and score < 4:
                    needs_revision = True
                    break
    
    if needs_revision:
        revision_notes = evaluation.get("revision_notes", "Improve clarity and accuracy.")
        rev_chain = _get_revision_chain("edge")
        
        perfected_response = rev_chain.invoke({
            "topic_a": topic_a,
            "topic_b": topic_b,
            "edge_signals": edge_signals,
            "context_snippets": context_text,
            "original_response": generated_response,
            "revision_notes": revision_notes,
        })
        return perfected_response.strip()
    
    return generated_response


def evaluate_and_revise_ranking_response(
    topic_list: str,
    user_question: str,
    generated_response: str,
) -> str:
    """Evaluate and revise ranking advice. Returns perfected response."""
    eval_chain = _get_evaluator_chain("ranking")
    
    eval_text = eval_chain.invoke({
        "topic_list": topic_list,
        "user_question": user_question,
        "generated_response": generated_response,
    })
    
    evaluation = _parse_json_response(eval_text)
    needs_revision = evaluation.get("needs_revision", False)
    
    if not needs_revision:
        for key, value in evaluation.items():
            if key not in ["needs_revision", "revision_notes"] and isinstance(value, dict):
                score = value.get("score")
                if score is not None and score < 4:
                    needs_revision = True
                    break
    
    if needs_revision:
        revision_notes = evaluation.get("revision_notes", "Improve clarity and accuracy.")
        rev_chain = _get_revision_chain("ranking")
        
        perfected_response = rev_chain.invoke({
            "topic_list": topic_list,
            "user_question": user_question,
            "original_response": generated_response,
            "revision_notes": revision_notes,
        })
        return perfected_response.strip()
    
    return generated_response


# Backward compatibility (will be removed after updating all callers)
def evaluate_topic_response(*args, **kwargs) -> Dict:
    """Deprecated: Use evaluate_and_revise_topic_response instead."""
    return {"overall_confidence": 100}


def evaluate_edge_response(*args, **kwargs) -> Dict:
    """Deprecated: Use evaluate_and_revise_edge_response instead."""
    return {"overall_confidence": 100}


def evaluate_ranking_response(*args, **kwargs) -> Dict:
    """Deprecated: Use evaluate_and_revise_ranking_response instead."""
    return {"overall_confidence": 100}
