# services/practice_questions_service.py
"""
Generate practice questions for a topic.
"""

import os
from typing import List, Tuple, Optional, Dict

from dotenv import load_dotenv
from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from services.evaluation_service import evaluate_and_revise_topic_response

load_dotenv()

_practice_chain = None


def _build_practice_chain():
    """Build chain for generating practice questions."""
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
                    "Your friend is asking you for practice questions to help them study.\n\n"
                    "**YOUR PERSONALITY:**\n"
                    "- You're super smart and know the material deeply, but you talk like a friend, not a textbook.\n"
                    "- You're friendly, warm, and encouraging - like you genuinely want to help your friend understand.\n"
                    "- You use natural, conversational language. No robotic or formal tone.\n\n"
                    "**HOW YOU GIVE PRACTICE QUESTIONS:**\n"
                    "- Create 2-3 good practice questions that will actually help them prepare for the exam.\n"
                    "- Vary question types (conceptual, calculation, application) - make them realistic.\n"
                    "- Include brief hints or answer guidance - you're helping them learn, not just testing them.\n"
                    "- Write them in a friendly, helpful way - like you're giving your friend study questions.\n"
                    "- Keep it concise but complete.\n"
                ),
            ),
            (
                "human",
                (
                    "Topic: {topic_name}\n"
                    "Importance: {importance_label}\n\n"
                    "Your friend asks for practice questions about this topic.\n\n"
                    "Give them good practice questions that will help them prepare for the exam. Be friendly and helpful."
                ),
            ),
        ]
    )

    parser = StrOutputParser()
    return prompt | llm | parser


def _get_practice_chain():
    global _practice_chain
    if _practice_chain is None:
        _practice_chain = _build_practice_chain()
    return _practice_chain


def generate_practice_questions(
    topic_name: str, 
    importance_label: str,
) -> str:
    """
    Generate practice questions for a topic.
    
    The questions are automatically evaluated and revised by the quality assurance evaluator
    before being returned. Students only see perfected questions.
    
    Returns:
        Perfected practice questions string
    """
    chain = _get_practice_chain()
    questions = chain.invoke({
        "topic_name": topic_name,
        "importance_label": importance_label,
    })
    
    # Quality assurance: Evaluate and revise questions before student sees them
    try:
        user_question = f"Generate practice exam questions for {topic_name}"
        perfected_questions = evaluate_and_revise_topic_response(
            topic_name=topic_name,
            importance_label=importance_label,
            user_question=user_question,
            generated_response=questions,
            context_snippets=None,
        )
        return perfected_questions
    except Exception as e:
        print(f"Evaluation/revision error (returning original): {e}")
        return questions


