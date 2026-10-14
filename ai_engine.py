"""
OmniBrain AI & Response Synthesis Engine
Synthesizes answers from stored memory using intelligent local heuristic/semantic RAG,
or seamlessly connects to Gemini / OpenAI APIs if an API key is provided.
Produces both formatted Markdown for chat and clean text for Voice (TTS).
"""

import re
import json
import requests
from typing import Dict, Any, List, Optional
import memory_engine

SYSTEM_PERSONA = (
    "You are T25-chatbot, an advanced AI assistant that learns and stores data for the user. "
    "You provide clear, accurate, and conversational answers via both text chat and voice. "
    "When relevant information is found in your stored memory, prioritize it and answer accurately. "
    "Keep answers conversational, engaging, and suitable for listening via voice."
)

def clean_for_speech(text: str) -> str:
    """
    Cleans markdown formatting, links, and code blocks
    so that browser Text-to-Speech sounds natural and fluent.
    """
    # Remove code blocks
    clean = re.sub(r'```[\s\S]*?```', ' [code snippet omitted] ', text)
    # Remove inline code
    clean = re.sub(r'`([^`]+)`', r'\1', clean)
    # Remove markdown images and links
    clean = re.sub(r'!\[.*?\]\(.*?\)', '', clean)
    clean = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', clean)
    # Remove bold, italics, strikethrough
    clean = re.sub(r'[\*_~]{1,3}', '', clean)
    # Remove markdown headers (# Title)
    clean = re.sub(r'#+\s*', '', clean)
    # Remove blockquotes and list bullets
    clean = re.sub(r'^\s*[-*+>]\s+', '', clean, flags=re.MULTILINE)
    # Replace multiple newlines or spaces with single space
    clean = re.sub(r'\n+', ' ', clean)
    clean = re.sub(r'\s{2,}', ' ', clean)
    return clean.strip()

def check_greeting_or_meta(message: str) -> Optional[str]:
    """Handles common conversational greetings and meta-questions locally."""
    msg = message.strip().lower()
    
    # Greetings
    if msg in ["hi", "hello", "hey", "greetings", "good morning", "good afternoon", "good evening", "sup"]:
        return (
            "Hello! I am **T25-chatbot**, your learning AI companion. You can teach me facts, notes, images, or documents, "
            "and I will store them and answer any questions you have via chat or voice. "
            "How can I help you today?"
        )
        
    # Who are you / What can you do
    if any(q in msg for q in ["who are you", "what are you", "what can you do", "introduce yourself", "help"]):
        return (
            "I am **T25-chatbot**, an adaptive AI assistant that can **learn and store data** for you!\n\n"
            "✨ **Key Capabilities:**\n"
            "- 🧠 **Learn in conversation:** Say *\"Remember that my dog is Charlie\"* or *\"Note down: project deadline is Nov 15\"*.\n"
            "- 🖼️ **Images & Vision:** Attach images to analyze and store visual knowledge.\n"
            "- 📄 **PDFs & Long Articles:** Upload multi-page PDFs to chunk and index into memory.\n"
            "- 🔗 **Website & Product Fetch:** Paste any URL or click 🔗 to extract product prices, ratings, or article text.\n"
            "- 📚 **Knowledge Base:** View, search, and manage all learned facts in the Knowledge Base tab.\n"
            "- 🎙️ **Voice Chat:** Speak directly using the microphone button or listen to answers with real-time Text-to-Speech!\n"
            "- ⚡ **100% Offline by Default:** Works instantly without any API keys, with optional Gemini/OpenAI integration."
        )
        
    # List memories / What do you know
    if any(q in msg for q in ["what do you know", "what have you learned", "show me your memory", "list memories", "what do you remember"]):
        memories = memory_engine.list_memories(limit=10)
        stats = memory_engine.get_stats()
        if not memories:
            return (
                "My memory is currently empty. You haven't taught me anything yet!\n\n"
                "Try saying: *\"Remember that my favorite book is Dune\"* or upload a document in the Knowledge Base tab."
            )
        summary = f"I currently hold **{stats['total_memories']} pieces of knowledge** across **{stats['total_categories']} categories**.\n\nHere are some things I remember:\n"
        for idx, m in enumerate(memories[:7], 1):
            summary += f"{idx}. **{m['title']}** ({m['category']}): {m['content'][:90]}{'...' if len(m['content']) > 90 else ''}\n"
        if len(memories) > 7:
            summary += f"\n*...and {stats['total_memories'] - 7} more. Check the Knowledge Base tab to view and manage all of them!*"
        return summary
        
    return None

def synthesize_local_answer(query: str, memories: List[Dict[str, Any]]) -> str:
    """
    Synthesizes an intelligent, context-aware conversational answer from retrieved memories
    completely offline without requiring any external LLM or API key.
    """
    if not memories:
        return (
            "I don't have information about that in my memory yet.\n\n"
            "💡 **You can teach me right now!**\n"
            "Just say: *\"Remember that...\"* followed by the details, or upload documents in the Knowledge Base tab."
        )
        
    top = memories[0]
    
    # If high confidence top match
    if len(memories) == 1 or top.get("relevance_score", 0) > 0.8:
        answer = f"Based on what you've taught me about **{top['title']}**:\n\n"
        answer += f"> {top['content']}\n\n"
        answer += f"*(Category: {top['category']})*"
        return answer
        
    # If multiple relevant memories found
    answer = f"Here is what I found in my memory regarding your question:\n\n"
    for i, m in enumerate(memories[:3], 1):
        answer += f"**{i}. {m['title']}** *({m['category']})*\n"
        answer += f"{m['content']}\n\n"
        
    answer += "Let me know if you would like more details or if you want to update this information!"
    return answer

def call_gemini_api(query: str, memories: List[Dict[str, Any]], api_key: str, model: str = "gemini-1.5-flash") -> str:
    """Calls Google Gemini API with RAG context grounding."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    
    context_str = ""
    if memories:
        context_str = "\n".join([f"- [{m['title']} | {m['category']}]: {m['content']}" for m in memories])
    else:
        context_str = "No specific memories found in the database for this question."
        
    prompt_text = (
        f"{SYSTEM_PERSONA}\n\n"
        f"--- STORED KNOWLEDGE FROM MEMORY ---\n{context_str}\n-----------------------------------\n\n"
        f"User Question: {query}\n\n"
        f"Please provide an accurate, friendly, and conversational answer. "
        f"If the answer is in the stored memory, rely on it. If not, state that it wasn't in memory and give helpful insights."
    )
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt_text}]
        }],
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 800
        }
    }
    
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, json=payload, headers=headers, timeout=20)
    response.raise_for_status()
    data = response.json()
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()

def call_openai_api(query: str, memories: List[Dict[str, Any]], api_key: str, model: str = "gpt-4o-mini") -> str:
    """Calls OpenAI API with RAG context grounding."""
    url = "https://api.openai.com/v1/chat/completions"
    
    context_str = ""
    if memories:
        context_str = "\n".join([f"- [{m['title']} | {m['category']}]: {m['content']}" for m in memories])
    else:
        context_str = "No specific memories found in the database."
        
    messages = [
        {"role": "system", "content": f"{SYSTEM_PERSONA}\n\n--- STORED KNOWLEDGE ---\n{context_str}"},
        {"role": "user", "content": query}
    ]
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.4,
        "max_tokens": 800
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    response = requests.post(url, json=payload, headers=headers, timeout=20)
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"].strip()

def call_ollama_api(
    query: str,
    memories: List[Dict[str, Any]],
    model: str = "llama3.2",
    base_url: str = "http://localhost:11434"
) -> str:
    """Calls a locally hosted Ollama model with retrieved memory as context."""
    context_str = "\n".join(
        f"- [{memory['title']} | {memory['category']}]: {memory['content']}"
        for memory in memories
    ) or "No specific memories were found in the local knowledge base."

    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {
                "role": "system",
                "content": (
                    f"{SYSTEM_PERSONA}\n\n"
                    "Use the following retrieved knowledge when it is relevant. "
                    "Do not claim it contains information it does not.\n\n"
                    f"--- RETRIEVED KNOWLEDGE ---\n{context_str}"
                )
            },
            {"role": "user", "content": query}
        ],
        "options": {"temperature": 0.4}
    }
    url = f"{base_url.rstrip('/')}/api/chat"
    response = requests.post(url, json=payload, timeout=120)
    response.raise_for_status()
    answer = response.json().get("message", {}).get("content", "").strip()
    if not answer:
        raise ValueError("Ollama returned an empty response")
    return answer

def process_user_message(message: str, session_id: str = "default") -> Dict[str, Any]:
    """
    Main pipeline:
    1. Checks if the user is teaching/storing data. If yes, memorizes immediately.
    2. Checks meta-conversations / greetings.
    3. Searches memory for relevant knowledge using hybrid RAG.
    4. Generates response using local offline synthesizer or configured AI API.
    5. Formats both rich markdown chat and clean speech text for voice.
    6. Stores in conversation history.
    """
    clean_message = message.strip()
    if not clean_message:
        return {
            "text": "Please provide a question or instruction.",
            "speech_text": "Please provide a question or instruction.",
            "sources": [],
            "learned": False
        }
        
    # Save user message to chat history
    memory_engine.save_chat_message(session_id=session_id, role="user", content=clean_message)
    
    # 1. Check for real-time learning / teaching intent
    learning_result = memory_engine.detect_and_learn_from_message(clean_message)
    if learning_result:
        resp_text = learning_result["response"]
        speech_text = clean_for_speech(resp_text)
        memory_engine.save_chat_message(
            session_id=session_id,
            role="assistant",
            content=resp_text,
            sources_used=[learning_result["memory"]["id"]]
        )
        return {
            "text": resp_text,
            "speech_text": speech_text,
            "sources": [learning_result["memory"]],
            "learned": True
        }
        
    # 2. Check for Website URL in message (Fetch product info / web article)
    website_memories = []
    url_match = re.search(r'https?://[^\s]+', clean_message)
    if url_match:
        import extractor_engine
        target_url = url_match.group(0).rstrip('.,;)"\'')
        url_res = extractor_engine.fetch_and_extract_url(target_url)
        if not url_res.get("success"):
            resp_text = f"I couldn't read that website: {url_res.get('error', 'Unknown error')}"
            memory_engine.save_chat_message(session_id=session_id, role="assistant", content=resp_text)
            return {
                "text": resp_text,
                "speech_text": clean_for_speech(resp_text),
                "sources": [],
                "learned": False,
                "is_url": True
            }

        website_memories = url_res.get("memories", [])
        website_question = (
            clean_message[:url_match.start()] + " " + clean_message[url_match.end():]
        ).strip(" \t\r\n-:,.!?;")
        if not website_question:
            resp_text = url_res["display_message"]
            speech_text = url_res["speech_text"]
            memory_engine.save_chat_message(
                session_id=session_id,
                role="assistant",
                content=resp_text,
                sources_used=[m["id"] for m in website_memories]
            )
            return {
                "text": resp_text,
                "speech_text": speech_text,
                "sources": website_memories,
                "learned": True,
                "is_url": True,
                "is_product": url_res.get("is_product", False)
            }
        clean_message = website_question

    # 3. Check greetings or meta queries
    meta_response = check_greeting_or_meta(clean_message)
    if meta_response:
        speech_text = clean_for_speech(meta_response)
        memory_engine.save_chat_message(session_id=session_id, role="assistant", content=meta_response)
        return {
            "text": meta_response,
            "speech_text": speech_text,
            "sources": [],
            "learned": False
        }
        
    # 3. Retrieve relevant memories via hybrid search
    relevant_memories = memory_engine.search_relevant_memories(
        clean_message,
        top_k=20 if website_memories else 4
    )
    if website_memories:
        website_memory_ids = {memory["id"] for memory in website_memories}
        page_matches = [memory for memory in relevant_memories if memory["id"] in website_memory_ids]
        relevant_memories = page_matches[:4] if page_matches else website_memories[:4]
    
    # 4. Generate response
    provider = memory_engine.get_setting("ai_provider", "local")
    resp_text = ""
    sources_used = relevant_memories if relevant_memories else []
    
    if provider == "gemini":
        gemini_key = memory_engine.get_setting("gemini_api_key", "").strip()
        gemini_model = memory_engine.get_setting("gemini_model", "gemini-1.5-flash").strip()
        if gemini_key:
            try:
                resp_text = call_gemini_api(clean_message, relevant_memories, gemini_key, gemini_model)
            except Exception as e:
                # Fallback to local on error
                local_ans = synthesize_local_answer(clean_message, relevant_memories)
                resp_text = f"> ⚠️ *Gemini API call failed ({str(e)}). Falling back to local memory engine:*\n\n{local_ans}"
        else:
            resp_text = synthesize_local_answer(clean_message, relevant_memories)
            
    elif provider == "openai":
        openai_key = memory_engine.get_setting("openai_api_key", "").strip()
        openai_model = memory_engine.get_setting("openai_model", "gpt-4o-mini").strip()
        if openai_key:
            try:
                resp_text = call_openai_api(clean_message, relevant_memories, openai_key, openai_model)
            except Exception as e:
                local_ans = synthesize_local_answer(clean_message, relevant_memories)
                resp_text = f"> ⚠️ *OpenAI API call failed ({str(e)}). Falling back to local memory engine:*\n\n{local_ans}"
        else:
            resp_text = synthesize_local_answer(clean_message, relevant_memories)

    elif provider == "ollama":
        ollama_model = memory_engine.get_setting("ollama_model", "llama3.2").strip()
        ollama_url = memory_engine.get_setting("ollama_url", "http://localhost:11434").strip()
        try:
            resp_text = call_ollama_api(clean_message, relevant_memories, ollama_model, ollama_url)
        except Exception as e:
            local_ans = synthesize_local_answer(clean_message, relevant_memories)
            resp_text = f"> ⚠️ *Ollama request failed ({str(e)}). Falling back to local memory engine:*\n\n{local_ans}"
            
    else:
        # Default local offline synthesis
        resp_text = synthesize_local_answer(clean_message, relevant_memories)
        
    speech_text = clean_for_speech(resp_text)
    
    # Save assistant response to conversation history
    source_ids = [m["id"] for m in sources_used]
    memory_engine.save_chat_message(
        session_id=session_id,
        role="assistant",
        content=resp_text,
        sources_used=source_ids
    )
    
    return {
        "text": resp_text,
        "speech_text": speech_text,
        "sources": sources_used,
        "learned": bool(website_memories),
        "is_url": bool(website_memories)
    }
