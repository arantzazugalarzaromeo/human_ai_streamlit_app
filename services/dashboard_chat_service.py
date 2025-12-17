# services/dashboard_chat_service.py
import os
from typing import Dict, List, Tuple, Optional

from dotenv import load_dotenv
from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from services.evaluation_service import evaluate_and_revise_ranking_response
from services.rag_service import retrieve_relevant_snippets, retrieve_co_occurrence_snippets
from services.practice_questions_service import generate_practice_questions
from services.edge_tutor_service import explain_topic_connection

load_dotenv()

_dashboard_chain = None
_teaching_chain = None


def _build_dashboard_chain():
    """Build chain for dashboard chat that handles multiple capabilities."""
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        raise RuntimeError(
            "MISTRAL_API_KEY is not set. Please create a .env file with your API key."
        )

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
                        "You're talking to your friend who needs help studying, and you're explaining things in a natural, friendly way.\n\n"
                        "**YOUR PERSONALITY:**\n"
                        "- You're super smart and know the material deeply, but you talk like a friend, not a textbook.\n"
                        "- You're friendly, warm, and encouraging - like you genuinely want to help your friend understand.\n"
                        "- You use natural, conversational language. No robotic or formal tone.\n"
                        "- You can answer any question they throw at you - teaching, connections, practice questions, whatever.\n"
                        "- You maintain context throughout the conversation - you remember what you talked about.\n\n"
                        "**HOW YOU EXPLAIN RANKINGS:**\n"
                        "- When they ask why something is ranked a certain way, look at the ACTUAL CONTENT and explain it naturally.\n"
                        "- Be specific: 'This is exam-critical because [specific reason based on what the topic actually is].'\n"
                        "- Make them understand: 'Oh, I get why this is important' or 'Oh, I see why this is extra.'\n"
                        "- Base it on the concepts, how they're used, their role - show you really understand the material.\n\n"
                        "**RESPONSE STYLE:**\n"
                        "- Write like you're texting a friend - natural, friendly, helpful.\n"
                        "- Keep answers concise but complete. One good paragraph is usually enough.\n"
                        "- Be conversational - it's a back-and-forth, not a lecture.\n\n"
                        "**USING THE SLIDES:**\n"
                        "- Use the context from their slides to ground your answers in what they actually uploaded.\n"
                        "- You know the slides well, so reference specific things when relevant.\n"
                        "- Always be accurate - don't make things up.\n"
                    ),
                ),
            (
                "human",
                (
                    "Here are the topics ranked by importance:\n{topics_list}\n\n"
                    "Your friend asks: {question}\n\n"
                    "Answer them naturally, like a smart friend would. Be helpful, clear, and friendly."
                ),
            ),
        ]
    )

    parser = StrOutputParser()
    return prompt | llm | parser


def _build_teaching_chain():
    """Build chain for teaching topics progressively."""
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
                        "You're talking to your friend who needs help studying, and you're explaining things in a natural, friendly way.\n\n"
                        "**YOUR PERSONALITY:**\n"
                        "- You're super smart and know the material deeply, but you talk like a friend, not a textbook.\n"
                        "- You're friendly, warm, and encouraging - like you genuinely want to help your friend understand.\n"
                        "- You use natural, conversational language. No robotic or formal tone.\n"
                        "- You can answer any question they throw at you - teaching, connections, practice questions, whatever.\n"
                        "- You maintain context throughout the conversation - you remember what you talked about.\n\n"
                        "**HOW YOU TEACH:**\n"
                        "- When they ask you to teach something, give them a clear, concise explanation that actually helps them understand.\n"
                        "- Don't give huge monologues - keep it concise but complete. Answer what they asked.\n"
                        "- If they ask a follow-up question, answer it naturally. You know what they're referring to.\n"
                        "- Use examples and analogies when helpful - that's how friends explain things.\n"
                        "- If they ask about connections between topics, explain how they relate naturally.\n"
                        "- If they ask for practice questions, give them good ones that test understanding.\n\n"
                        "**RESPONSE STYLE:**\n"
                        "- Write like you're texting a friend - natural, friendly, helpful.\n"
                        "- Keep answers concise but complete. One good paragraph is usually enough, unless they ask for more detail.\n"
                        "- Don't force them to say 'continue' - just answer their questions naturally.\n"
                        "- If they ask something new, switch topics naturally. You're having a conversation.\n\n"
                        "**USING THE SLIDES:**\n"
                        "- Use the context from their slides to ground your answers in what they actually uploaded.\n"
                        "- You know the slides well, so reference specific things when relevant.\n"
                        "- If something isn't in the slides but you know it's important, you can mention it (you're a smart friend, after all).\n"
                        "- Always be accurate - don't make things up.\n"
                    ),
                ),
            (
                "human",
                (
                    "Topic: {topic_name}\n"
                    "Importance: {importance_label}\n\n"
                    "{context}\n\n"
                    "Your friend asks: {question}\n\n"
                    "Answer them naturally, like a smart friend would. Be helpful, clear, and friendly."
                ),
            ),
        ]
    )

    parser = StrOutputParser()
    return prompt | llm | parser


def _get_dashboard_chain():
    global _dashboard_chain
    if _dashboard_chain is None:
        _dashboard_chain = _build_dashboard_chain()
    return _dashboard_chain


def _get_teaching_chain():
    global _teaching_chain
    if _teaching_chain is None:
        _teaching_chain = _build_teaching_chain()
    return _teaching_chain


def _detect_intent(question: str, topics: List[Dict], is_teaching_context: bool = False, previous_messages: Optional[List[Dict]] = None) -> str:
    """Detect what the user is asking for: ranking, teaching, connection, or practice."""
    question_lower = question.lower().strip()
    
    # Check if this is a follow-up question (uses "it", "this", "that", "they", etc.)
    is_followup = any(word in question_lower for word in ["it", "this", "that", "they", "is it", "does it", "can it", "are they"])
    
    # If it's a follow-up and we have context, try to infer intent from context
    if is_followup and previous_messages:
        # Look at the last assistant message to understand context
        for msg in reversed(previous_messages):
            if msg.get("role") == "assistant":
                last_content = msg.get("content", "").lower()
                # If last message was about a topic, this is likely a follow-up about that topic
                if any(word in last_content for word in ["think-aloud", "think aloud", "protocol", "usability"]):
                    # Check what kind of follow-up
                    if any(word in question_lower for word in ["related", "connect", "link", "relationship"]):
                        return "connection"
                    elif any(word in question_lower for word in ["practice", "question", "exercise"]):
                        return "practice"
                    else:
                        # General follow-up - treat as teaching/explanation continuation
                        return "teaching"
                break
    
    # If we're in teaching context and user says continue/next/more, stay in teaching
    if is_teaching_context and any(word in question_lower for word in ["continue", "next", "more", "go on", "yes", "understood", "ok", "okay", "sure", "please"]):
        return "teaching"
    
    # Check for practice questions
    if any(word in question_lower for word in ["practice", "question", "exercise", "quiz", "test"]):
        return "practice"
    
    # Check for connections (but handle follow-ups naturally)
    if any(word in question_lower for word in ["connect", "relationship", "related", "link", "how are", "between", "is it related", "does it relate"]):
        return "connection"
    
    # Check for teaching (teach, explain, learn about, what is, tell me about)
    if any(word in question_lower for word in ["teach", "explain", "learn about", "what is", "tell me about", "help me understand", "what are"]):
        return "teaching"
    
    # Check for ranking (why, important, ranked, priority)
    if any(word in question_lower for word in ["why", "important", "ranked", "priority", "focus"]):
        return "ranking"
    
    # If in teaching context and unclear, assume teaching continuation
    if is_teaching_context:
        return "teaching"
    
    # If it's a follow-up question without clear intent, default to teaching (natural conversation)
    if is_followup:
        return "teaching"
    
    # Default to ranking if unclear
    return "ranking"


def _extract_topic_names(question: str, topics: List[Dict]) -> Optional[Tuple[str, Optional[str]]]:
    """Extract topic name(s) from question. Returns (topic_name, second_topic_name) for connections."""
    question_lower = question.lower()
    topic_names = [t.get("name", "").lower() for t in topics]
    
    # Find mentioned topics
    found_topics = []
    for topic in topics:
        topic_name = topic.get("name", "")
        if topic_name.lower() in question_lower:
            found_topics.append(topic_name)
    
    if len(found_topics) >= 2:
        return (found_topics[0], found_topics[1])
    elif len(found_topics) == 1:
        return (found_topics[0], None)
    
    # Try to find by partial match
    for topic in topics:
        topic_name = topic.get("name", "")
        topic_words = topic_name.lower().split()
        if any(word in question_lower for word in topic_words if len(word) > 4):
            return (topic_name, None)
    
    return None


def ask_about_rankings(topics: List[Dict], question: str, text_dict: Optional[Dict[str, str]] = None, structured_slides: Optional[Dict] = None, part_tracking: Optional[int] = None, teaching_topic: Optional[str] = None, previous_messages: Optional[List[Dict]] = None) -> str:
    """
    Handle all dashboard chat capabilities:
    1. Explain why topics were ranked
    2. Teach topics (progressive)
    3. Explain connections
    4. Generate practice questions
    
    Returns:
        Perfected response string
    """
    # Detect intent - check if we're in teaching context
    is_teaching_context = teaching_topic is not None and part_tracking is not None
    intent = _detect_intent(question, topics, is_teaching_context, previous_messages)
    
    # Format topics list
    topics_text = []
    topics_detailed = []
    for i, topic in enumerate(topics, 1):
        name = topic.get("name", "Unknown")
        importance = topic.get("importance", "extra")
        score = topic.get("score", 0)
        topics_text.append(f"{i}. {name} ({importance})")
        topics_detailed.append(f"{i}. {name} - {importance} (score: {score:.1f})")
    
    topics_list = "\n".join(topics_text)
    topics_detailed_str = "\n".join(topics_detailed)
    
    # Route to appropriate handler
    if intent == "practice":
        # Generate practice questions
        topic_info = _extract_topic_names(question, topics)
        
        # If no topic found in current question, check conversation context
        if (not topic_info or not topic_info[0]) and previous_messages:
            # Look for topics mentioned in recent conversation
            recent_text = " ".join([msg.get("content", "") for msg in previous_messages[-4:]])
            topic_info = _extract_topic_names(recent_text + " " + question, topics)
        
        if topic_info and topic_info[0]:
            topic_name = topic_info[0]
            # Find topic importance
            topic_obj = next((t for t in topics if t.get("name", "").lower() == topic_name.lower()), None)
            importance = topic_obj.get("importance", "core") if topic_obj else "core"
            importance_label = f"{importance} topic"
            
            questions = generate_practice_questions(topic_name, importance_label)
            return questions
        else:
            # No specific topic mentioned - generate practice questions for the whole lecture
            # Use the teaching chain to generate questions naturally
            if previous_messages:
                # Get recent topics discussed
                recent_text = " ".join([msg.get("content", "") for msg in previous_messages[-4:]])
                topic_info = _extract_topic_names(recent_text, topics)
                if topic_info and topic_info[0]:
                    topic_name = topic_info[0]
                    topic_obj = next((t for t in topics if t.get("name", "").lower() == topic_name.lower()), None)
                    importance = topic_obj.get("importance", "core") if topic_obj else "core"
                    importance_label = f"{importance} topic"
                    questions = generate_practice_questions(topic_name, importance_label)
                    return questions
            
            # Generate practice questions for exam-critical topics or all topics
            # Pick the most important topics
            exam_critical_topics = [t for t in topics if t.get("importance") == "exam_critical"]
            core_topics = [t for t in topics if t.get("importance") == "core"]
            
            # Use exam-critical topics if available, otherwise core topics
            selected_topics = exam_critical_topics[:3] if exam_critical_topics else core_topics[:3]
            
            if selected_topics:
                # Generate questions for the first important topic
                topic_name = selected_topics[0].get("name", "")
                importance = selected_topics[0].get("importance", "core")
                importance_label = f"{importance} topic"
                questions = generate_practice_questions(topic_name, importance_label)
                return questions
            elif topics:
                # Fallback to first topic
                topic_name = topics[0].get("name", "")
                importance = topics[0].get("importance", "core")
                importance_label = f"{importance} topic"
                questions = generate_practice_questions(topic_name, importance_label)
                return questions
            else:
                return "I'd love to give you practice questions! Could you tell me which topic you'd like to practice, or I can generate questions for the most important topics from your materials."
    
    elif intent == "connection":
        # Explain connections - handle both explicit and implicit (follow-up) questions
        topic_info = _extract_topic_names(question, topics)
        
        # If topics not explicitly mentioned, try to infer from conversation context
        if (not topic_info or not topic_info[0] or not topic_info[1]) and previous_messages:
            # Look for topics mentioned in recent conversation
            recent_text = " ".join([msg.get("content", "") for msg in previous_messages[-4:]])
            # Try to extract topics from recent conversation
            topic_info = _extract_topic_names(recent_text + " " + question, topics)
        
        if topic_info and topic_info[0] and topic_info[1]:
            topic_a = topic_info[0]
            topic_b = topic_info[1]
            
            # Get context snippets
            context_snippets = []
            if text_dict and structured_slides:
                context_snippets = retrieve_co_occurrence_snippets(
                    topic_a, topic_b, text_dict, structured_slides, max_snippets=5
                )
            
            # Pass the original question and conversation context for natural response
            answer = explain_topic_connection(topic_a, topic_b, question, context_snippets)
            return answer
        else:
            # If we still can't find topics, answer naturally as a friend would
            # Use the teaching chain to answer the question naturally
            if previous_messages:
                # Get the last topic mentioned
                recent_text = " ".join([msg.get("content", "") for msg in previous_messages[-2:]])
                topic_info = _extract_topic_names(recent_text, topics)
                if topic_info and topic_info[0]:
                    # Answer about the connection naturally
                    topic_name = topic_info[0]
                    # Use teaching chain to answer naturally
                    topic_obj = next((t for t in topics if t.get("name", "").lower() == topic_name.lower()), None)
                    importance = topic_obj.get("importance", "core") if topic_obj else "core"
                    importance_label = f"{importance} topic"
                    
                    context_snippets = []
                    context_text = ""
                    if text_dict:
                        if structured_slides:
                            context_snippets = retrieve_relevant_snippets(
                                topic_name, text_dict, structured_slides=structured_slides, max_snippets=5
                            )
                        else:
                            context_snippets = retrieve_relevant_snippets(
                                topic_name, text_dict, max_snippets=5
                            )
                        
                        if context_snippets:
                            context_text = "\n\nRelevant excerpts from your materials:\n"
                            for i, snippet in enumerate(context_snippets[:3], 1):
                                context_text += f"\n[{i}] {snippet[:300]}...\n"
                    
                    # Add conversation context
                    conversation_context = ""
                    if previous_messages:
                        recent_messages = previous_messages[-4:]
                        conversation_context = "\n\n**Recent conversation:**\n"
                        for msg in recent_messages:
                            role = msg.get("role", "")
                            content = msg.get("content", "")[:150]
                            if role == "user":
                                conversation_context += f"Friend: {content}...\n"
                            elif role == "assistant":
                                conversation_context += f"You: {content}...\n"
                        conversation_context += "\n(Use this context to answer naturally.)\n"
                    
                    chain = _get_teaching_chain()
                    answer = chain.invoke({
                        "topic_name": topic_name,
                        "importance_label": importance_label,
                        "context": context_text + conversation_context,
                        "question": question,
                    })
                    return answer
            
            # Last resort: answer naturally without specific topics
            return "I'd love to help you understand how topics connect! Could you tell me which two topics you're curious about? Or if you're asking about something we just discussed, I can explain that too!"
    
    elif intent == "teaching":
        # Teach topic - handle both explicit and follow-up questions naturally
        # If we're already teaching a topic, use that topic
        if teaching_topic:
            topic_name = teaching_topic
        else:
            # Extract topic name from question
            topic_info = _extract_topic_names(question, topics)
            
            # If no topic found in current question, check conversation context
            if (not topic_info or not topic_info[0]) and previous_messages:
                # Look for topics mentioned in recent conversation
                recent_text = " ".join([msg.get("content", "") for msg in previous_messages[-4:]])
                topic_info = _extract_topic_names(recent_text + " " + question, topics)
            
            if topic_info and topic_info[0]:
                topic_name = topic_info[0]
            else:
                # If still no topic, answer naturally about what they're asking
                # Use a generic topic name and let the LLM handle it naturally
                topic_name = "the topic you're asking about"
        
        # Find topic importance (if we have a real topic name)
        if topic_name and topic_name != "the topic you're asking about":
            topic_obj = next((t for t in topics if t.get("name", "").lower() == topic_name.lower()), None)
            importance = topic_obj.get("importance", "core") if topic_obj else "core"
            importance_label = f"{importance} topic"
        else:
            importance_label = "general topic"
        
        # Check if user wants to continue or needs re-explanation
        question_lower = question.lower()
        move_to_next = any(word in question_lower for word in ["continue", "next", "more", "go on", "keep going", "yes", "understood"])
        re_explain = any(word in question_lower for word in ["understand better", "explain again", "don't get it", "confused", "no"])
        
        # Build teaching question - natural conversation style
        # Always use the original question to maintain natural conversation flow
        teaching_question = question
        
        # Get context snippets using RAG (only if we have a real topic name)
        context_snippets = []
        context_text = ""
        if text_dict and topic_name and topic_name != "the topic you're asking about":
            if structured_slides:
                context_snippets = retrieve_relevant_snippets(
                    topic_name, text_dict, structured_slides=structured_slides, max_snippets=5
                )
            else:
                context_snippets = retrieve_relevant_snippets(
                    topic_name, text_dict, max_snippets=5
                )
            
            if context_snippets:
                context_text = "\n\nRelevant excerpts from your materials:\n"
                for i, snippet in enumerate(context_snippets[:3], 1):
                    context_text += f"\n[{i}] {snippet[:300]}...\n"
        
        # Add conversation history for context (so the friend remembers what was discussed)
        conversation_context = ""
        if previous_messages:
            # Include recent conversation for context
            recent_messages = previous_messages[-4:]  # Last 4 messages (2 exchanges)
            conversation_context = "\n\n**Recent conversation:**\n"
            for msg in recent_messages:
                role = msg.get("role", "")
                content = msg.get("content", "")[:150]  # Truncate for context
                if role == "user":
                    conversation_context += f"Friend: {content}...\n"
                elif role == "assistant":
                    conversation_context += f"You: {content}...\n"
            conversation_context += "\n(Use this context to maintain a natural conversation flow.)\n"
        
        chain = _get_teaching_chain()
        answer = chain.invoke({
            "topic_name": topic_name,
            "importance_label": importance_label,
            "context": context_text + conversation_context,
            "question": teaching_question,
        })
        
        return answer
    
    else:
        # Default: Explain rankings
        chain = _get_dashboard_chain()
        answer = chain.invoke({
            "topics_list": topics_list,
            "question": question,
        })
        
        # Quality assurance
        try:
            perfected_answer = evaluate_and_revise_ranking_response(
                topic_list=topics_detailed_str,
                user_question=question,
                generated_response=answer,
            )
            return perfected_answer
        except Exception as e:
            print(f"Evaluation/revision error (returning original): {e}")
            return answer
