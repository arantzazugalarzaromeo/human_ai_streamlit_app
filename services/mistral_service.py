# services/mistral_service.py
import os
from typing import Dict, List, Tuple, Optional

from dotenv import load_dotenv
from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from services.evaluation_service import evaluate_and_revise_topic_response

# Load environment variables from .env file
load_dotenv()

# We keep a single global chain so it's not rebuilt every time
_topic_chain = None


def _build_topic_chain():
    """
    Build a LangChain Runnable that:
    - uses a friendly, reassuring tutor persona
    - explains a specific topic at exam-appropriate depth
    """
    # Get API key from environment (supports both .env file and env vars)
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        raise RuntimeError(
            "MISTRAL_API_KEY is not set in your environment. "
            "Please create a .env file with MISTRAL_API_KEY=your_key or export it as an environment variable."
        )

    llm = ChatMistralAI(
        model="mistral-small-latest",  # or "mistral-large-latest" if you prefer
        temperature=0.3,
        max_retries=2,
        api_key=api_key,  # Explicitly pass the API key
    )

    prompt = ChatPromptTemplate.from_messages(
        [
                (
                    "system",
                    (
                        "You are a really smart student friend who understood the whole lecture perfectly. "
                        "You're explaining things to another student - you know a LOT about the topic, but you talk simply because you're a student too. "
                        "You're like that one student who can explain the whole lecture in a day while the teacher took two months.\n\n"
                        "**Key principles (MAINTAIN CONSISTENT QUALITY):**\n"
                        "- You're SMART and know the material deeply, but explain it simply like a friend would.\n"
                        "- Use SIMPLE, EASY-TO-READ language. Avoid complicated words. Write like you're talking to a friend.\n"
                        "- Be VERY friendly and reassuring. Make the student feel calm and confident.\n"
                        "- Give PROPER, DETAILED explanations - not just bullet points. Use full paragraphs and explanations.\n"
                        "- For exam-critical or core topics: go into the right depth - explain concepts, how they work, why they matter.\n"
                        "- For extra topics: keep it simpler and more conceptual.\n"
                        "- Filter out unnecessary or overly complicated details that don't appear in exam questions.\n"
                        "- Match the depth to what is actually needed for the exam based on the topic importance.\n"
                        "- **CRITICAL: Maintain the SAME high quality in EVERY response, regardless of how many questions the student asks.**\n"
                        "- **CRITICAL: Be accurate, consistent, and thorough in ALL your answers - quality should never degrade.**\n"
                        "- **CRITICAL: Always ground your answers in the provided context snippets - never make up information.**\n"
                        "- **CRITICAL: If you're uncertain about something, acknowledge it honestly rather than guessing.**\n\n"
                        "**CRITICAL FORMATTING REQUIREMENTS:**\n"
                        "1. After your main explanation, you MUST include a clearly separated section with this EXACT heading: **📋 What I Didn't Mention from the Slides**\n"
                        "   - In this section, you MUST list ALL topics, teachings, concepts, subtopics, examples, edge cases, and details from the slides that you didn't include.\n"
                        "   - Be COMPREHENSIVE - mention everything from the slides that was filtered out.\n"
                        "   - For each item, briefly explain why it wasn't included (usually because it doesn't appear in exam questions).\n"
                        "   - Format the heading in BOLD (**text**) and ensure the section is clearly separated with blank lines.\n\n"
                        "2. At the very end, you MUST include another clearly separated section with this EXACT heading: **🎯 What You Can Do Next**\n"
                        "   - List these options: a) deeper understanding (include the removed parts), b) more conceptual explanation if it's hard to understand, c) practice questions.\n"
                        "   - Format the heading in BOLD (**text**) and make it visually distinct.\n"
                        "   - Ensure this section is clearly separated from the previous section with blank lines."
                    ),
                ),
            (
                "human",
                (
                    "Current topic: {topic_name}\n"
                    "Topic importance: {importance_label}\n\n"
                    "Student question:\n{question}\n\n"
                    "Answer directly to the student."
                ),
            ),
        ]
    )

    parser = StrOutputParser()
    chain = prompt | llm | parser
    return chain


def _get_topic_chain():
    global _topic_chain
    if _topic_chain is None:
        _topic_chain = _build_topic_chain()
    return _topic_chain


def ask_mistral_about_topic(
    topic_name: str, 
    importance_label: str, 
    question: str, 
    context_snippets: List[str] = None,
) -> str:
    """
    Helper used by the topic tutor chat.
    Now supports RAG with context snippets.
    
    The response is automatically evaluated and revised by the quality assurance evaluator
    before being returned. Students only see perfected responses.
    
    Returns:
        Perfected response string (evaluated and revised if needed)
    """
    # Build context text if snippets provided
    context_text = ""
    if context_snippets:
        context_text = "\n\nRelevant excerpts from your materials:\n"
        for i, snippet in enumerate(context_snippets[:3], 1):
            context_text += f"\n[{i}] {snippet[:300]}...\n"
    
    # Update prompt to include context
    if context_snippets:
        prompt = ChatPromptTemplate.from_messages(
            [
                    (
                        "system",
                        (
                            "You are a really smart student friend who understood the whole lecture perfectly. "
                            "You're explaining things to another student - you know a LOT about the topic, but you talk simply because you're a student too.\n\n"
                            "**CRITICAL: PROGRESSIVE EXPLANATION APPROACH**\n"
                            "When a student asks you to teach them about a topic:\n"
                            "1. FIRST response: Give just ONE small paragraph (3-4 sentences) with a brief overview of the topic.\n"
                            "2. Add a tiny 2-sentence summary starting with 'In summary:' that tells them exactly what they need to know.\n"
                            "3. End with: 'Would you like to continue learning about this topic, or do you want to understand this part better before moving on?'\n"
                            "4. Wait for the student to say they want to continue before explaining more.\n"
                            "5. When they continue, explain the next aspect in ONE paragraph + summary, then ask if they want to continue.\n"
                            "6. Continue this pattern until you've explained everything about the topic.\n"
                            "7. At the very end, say: 'I've told you everything you need to know about this topic. Let me know if you want to learn about a new topic or if you want some practice questions.'\n\n"
                            "**IMPORTANT:**\n"
                            "- NEVER give one big message with multiple parts (A, B, C, D) all at once.\n"
                            "- Start with just a brief overview, then wait for the student to continue.\n"
                            "- Each response should be ONE paragraph + summary + question to continue.\n"
                            "- Keep responses SHORT and COMPACT - students don't like huge text blocks.\n\n"
                            "**Key principles:**\n"
                            "- You're SMART and know the material deeply, but explain it simply like a friend would.\n"
                            "- Use SIMPLE, EASY-TO-READ language. Avoid complicated words.\n"
                            "- Be VERY friendly and reassuring. Make the student feel calm and confident.\n"
                            "- For exam-critical or core topics: go into the right depth - explain concepts, how they work, why they matter.\n"
                            "- For extra topics: keep it simpler and more conceptual.\n"
                            "- Filter out unnecessary or overly complicated details that don't appear in exam questions.\n"
                            "- Use the provided context from their materials to ground your answer in what they actually uploaded.\n"
                            "- **CRITICAL: Always ground your answers in the provided context snippets - never make up information.**\n"
                            "- **CRITICAL: If you're uncertain about something, acknowledge it honestly rather than guessing.**\n"
                            "- **CRITICAL: Break complex topics into logical parts - don't overwhelm the student with everything at once.**"
                        ),
                    ),
                (
                    "human",
                    (
                        "Current topic: {topic_name}\n"
                        "Topic importance: {importance_label}\n\n"
                        "{context}\n\n"
                        "Student question:\n{question}\n\n"
                        "Answer directly to the student, using the context when relevant."
                    ),
                ),
            ]
        )
        
        parser = StrOutputParser()
        llm = ChatMistralAI(
            model="mistral-small-latest",
            temperature=0.3,
            max_retries=2,
            api_key=os.environ.get("MISTRAL_API_KEY"),
        )
        chain = prompt | llm | parser
        
        answer = chain.invoke({
            "topic_name": topic_name,
            "importance_label": importance_label,
            "context": context_text,
            "question": question,
        })
    else:
        # Original behavior without context
        chain = _get_topic_chain()
        inputs: Dict[str, str] = {
            "topic_name": topic_name,
            "importance_label": importance_label,
            "question": question,
        }
        answer = chain.invoke(inputs)
    
    # Quality assurance: Evaluate and revise response before student sees it
    # The evaluator acts as a strict teaching assistant that perfects the response
    try:
        perfected_answer = evaluate_and_revise_topic_response(
            topic_name=topic_name,
            importance_label=importance_label,
            user_question=question,
            generated_response=answer,
            context_snippets=context_snippets,
        )
        return perfected_answer
    except Exception as e:
        print(f"Evaluation/revision error (returning original): {e}")
        # If evaluator fails, return original (shouldn't happen, but safety fallback)
        return answer
