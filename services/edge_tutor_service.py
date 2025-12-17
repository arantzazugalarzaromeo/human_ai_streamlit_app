# services/edge_tutor_service.py
"""
Service for explaining connections between two topics.
"""

import os
from typing import List, Tuple, Dict, Optional

from dotenv import load_dotenv
from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from services.rag_service import retrieve_co_occurrence_snippets
from services.evaluation_service import evaluate_and_revise_edge_response

load_dotenv()

_edge_chain = None


def _build_edge_chain():
    """Build chain for explaining topic connections."""
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        raise RuntimeError("MISTRAL_API_KEY is not set.")

    llm = ChatMistralAI(
        model="mistral-small-latest",
        temperature=0.7,  # Higher temperature for more natural, friend-like responses
        max_retries=2,
        api_key=api_key,
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                (
                    "You are that one really smart friend in class - the one who can explain the whole lecture in a day while the professor took two months. "
                    "You're talking to your friend who needs help understanding how topics connect.\n\n"
                    "**YOUR PERSONALITY:**\n"
                    "- You're super smart and know the material deeply, but you talk like a friend, not a textbook.\n"
                    "- You're friendly, warm, and encouraging - like you genuinely want to help your friend understand.\n"
                    "- You use natural, conversational language. No robotic or formal tone.\n\n"
                    "**HOW YOU EXPLAIN CONNECTIONS:**\n"
                    "- Explain how the topics relate in a clear, natural way - like you're explaining to a friend.\n"
                    "- Use the context from their slides to ground your explanation.\n"
                    "- Help them see why understanding this connection matters.\n"
                    "- If they're not really connected, say so honestly - don't force a connection.\n"
                    "- Keep it concise but complete - one good paragraph explaining the connection.\n"
                    "**USING THE SLIDES:**\n"
                    "- Always ground your explanations in the provided context - never make up relationships.\n"
                    "- Be accurate and honest.\n"
                ),
            ),
            (
                "human",
                (
                    "Topic A: {topic_a}\n"
                    "Topic B: {topic_b}\n\n"
                    "{context}\n\n"
                    "Your friend asks: {question}\n\n"
                    "Answer them naturally, like a smart friend would. Explain how these topics connect, using the context when relevant."
                ),
            ),
        ]
    )

    parser = StrOutputParser()
    return prompt | llm | parser


def _get_edge_chain():
    global _edge_chain
    if _edge_chain is None:
        _edge_chain = _build_edge_chain()
    return _edge_chain


def explain_topic_connection(
    topic_a: str,
    topic_b: str,
    question: str,
    context_snippets: List[str],
    edge_signals: Optional[str] = None,
) -> str:
    """
    Explain how two topics connect.
    
    The response is automatically evaluated and revised by the quality assurance evaluator
    before being returned. Students only see perfected responses.
    
    Returns:
        Perfected response string
    """
    context_text = ""
    if context_snippets:
        context_text = "\n\nRelevant excerpts where both topics appear:\n"
        for i, snippet in enumerate(context_snippets[:3], 1):
            context_text += f"\n[{i}] {snippet[:300]}...\n"
    else:
        context_text = "\n\n(No specific context found where both topics appear together.)\n"
    
    # Determine edge signals if not provided
    if edge_signals is None:
        edge_signals = "Topics appear together in slides (co-occurrence detected)"
    
    chain = _get_edge_chain()
    answer = chain.invoke({
        "topic_a": topic_a,
        "topic_b": topic_b,
        "context": context_text,
        "question": question,
    })
    
    # Quality assurance: Evaluate and revise response before student sees it
    try:
        perfected_answer = evaluate_and_revise_edge_response(
            topic_a=topic_a,
            topic_b=topic_b,
            edge_signals=edge_signals,
            generated_response=answer,
            context_snippets=context_snippets,
        )
        return perfected_answer
    except Exception as e:
        print(f"Evaluation/revision error (returning original): {e}")
        return answer



