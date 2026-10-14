"""
T25 Document Analysis & Research Engine
Runs in the background after a document is uploaded:
1. Analyses the document with the configured AI model (summary, key points, topics)
2. Researches its main topics on the web (DuckDuckGo, no API key) and stores useful pages
3. Writes a research brief that connects the document to what was found online
Everything is saved to memory so it can be used in future conversations.
"""

import os
import re
import json
import threading
from collections import Counter
from typing import Dict, Any, List, Optional

import requests
from bs4 import BeautifulSoup

import memory_engine
import ai_engine
from extractor_engine import HEADERS, chunk_text

# Limits keep a full run to a few minutes on a CPU-only local model
ANALYSIS_INPUT_CHARS = 9000
MAX_QUERIES = 3
RESULTS_PER_QUERY = 3
MAX_PAGES = 5
CHUNKS_PER_PAGE = 3
BRIEF_SOURCE_CHARS = 1200

def sample_text(text: str, limit: int) -> str:
    """Returns the whole text if short, otherwise evenly spaced windows covering the document."""
    if len(text) <= limit:
        return text
    pieces = 6
    window = limit // pieces
    step = (len(text) - window) // (pieces - 1)
    return "\n[...]\n".join(text[i * step:i * step + window] for i in range(pieces))

def parse_json(raw: str) -> Dict[str, Any]:
    """Parses a JSON object from model output, tolerating surrounding prose or code fences."""
    try:
        return json.loads(raw)
    except Exception:
        match = re.search(r'\{[\s\S]*\}', raw or "")
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
    return {}

def as_list(value: Any) -> List[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    return [str(v).strip() for v in value if str(v).strip()]

def keyword_topics(text: str, count: int = 5) -> List[str]:
    """Offline fallback: the most frequent meaningful words in the document."""
    words = [w for w in memory_engine.extract_keywords(text) if len(w) > 3 and not w.isdigit()]
    return [w for w, _ in Counter(words).most_common(count)]

def analyse_document(text: str, filename: str) -> Dict[str, Any]:
    """Asks the AI model for a structured analysis. Falls back to a heuristic outline."""
    prompt = (
        f'Analyse the document below (file name: "{filename}"). '
        "Respond with a JSON object only, using exactly these keys:\n"
        '{"title": "short descriptive title", '
        '"document_type": "e.g. research paper, invoice, contract, manual, report", '
        '"summary": "a 5-8 sentence summary of what the document says", '
        '"key_points": ["5-8 most important facts, figures, findings, dates or obligations"], '
        '"topics": ["3-6 main subjects"], '
        '"search_queries": ["2-3 specific web search queries to research and verify the main subject"]}\n'
        "Search queries must name the specific entities, products, methods or terms in the document, "
        "not generic words.\n\n"
        f"DOCUMENT:\n{sample_text(text, ANALYSIS_INPUT_CHARS)}"
    )
    raw = ai_engine.generate_text(
        prompt,
        system="You are a careful analyst. Only state what the document supports.",
        json_mode=True,
        max_tokens=900
    )
    data = parse_json(raw) if raw else {}

    base_name = os.path.splitext(filename)[0].replace("_", " ").replace("-", " ").strip()
    topics = as_list(data.get("topics")) or keyword_topics(text)
    queries = as_list(data.get("search_queries"))
    if not queries:
        queries = [f"{base_name} {' '.join(topics[:3])}".strip()]
    if not data.get("summary"):
        sentences = re.split(r'(?<=[.!?])\s+', re.sub(r'\s+', ' ', text[:3000]))
        data["summary"] = " ".join(sentences[:5])

    return {
        "title": str(data.get("title") or base_name).strip(),
        "document_type": str(data.get("document_type") or "Document").strip(),
        "summary": str(data["summary"]).strip(),
        "key_points": as_list(data.get("key_points")),
        "topics": topics,
        "search_queries": queries[:MAX_QUERIES],
        "used_ai": bool(raw)
    }

def web_search(queries: List[str]) -> List[Dict[str, str]]:
    """Searches the web for each query and returns unique results."""
    try:
        from ddgs import DDGS
    except ImportError:
        return []

    results, seen = [], set()
    for query in queries:
        try:
            hits = DDGS().text(query, max_results=RESULTS_PER_QUERY) or []
        except Exception:
            continue
        for hit in hits:
            url = hit.get("href", "")
            if not url.startswith(("http://", "https://")) or url in seen:
                continue
            seen.add(url)
            results.append({
                "title": hit.get("title", url).strip(),
                "url": url,
                "snippet": hit.get("body", "").strip(),
                "query": query
            })
    return results

def fetch_page_text(url: str) -> str:
    """Downloads a web page and returns its readable body text (empty string on failure)."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=12)
        resp.raise_for_status()
        if "html" not in resp.headers.get("Content-Type", "html"):
            return ""
    except Exception:
        return ""

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg", "aside", "form"]):
        tag.decompose()
    main = soup.find("article") or soup.find("main") or soup.body
    if not main:
        return ""
    paragraphs = [
        p.get_text(" ", strip=True)
        for p in main.find_all(["p", "h2", "h3", "li", "blockquote"])
    ]
    return "\n\n".join(p for p in paragraphs if len(p) > 40)

def research_topics(analysis: Dict[str, Any], filename: str) -> Dict[str, Any]:
    """Runs web searches, stores the useful pages in memory, and returns the sources."""
    sources = []
    memories = []
    for result in web_search(analysis["search_queries"]):
        if len(sources) >= MAX_PAGES:
            break
        page_text = fetch_page_text(result["url"])
        if len(page_text) < 200 and not result["snippet"]:
            continue
        result["text"] = page_text or result["snippet"]
        sources.append(result)

        for idx, chunk in enumerate(chunk_text(result["text"], chunk_size=900)[:CHUNKS_PER_PAGE], 1):
            memories.append(memory_engine.add_memory(
                title=f"Research: {result['title'][:50]} (Part {idx})",
                content=f"Source: {result['url']}\n\n{chunk}",
                category="Research",
                tags=f"research, {filename}, {', '.join(analysis['topics'][:4])}",
                source=f"research:{filename}"
            ))
    return {"sources": sources, "memories": memories}

def write_research_brief(analysis: Dict[str, Any], sources: List[Dict[str, Any]]) -> str:
    """Asks the AI model to connect the document with the web research."""
    if not sources:
        return "No web results could be retrieved for this document's topics (check the internet connection)."

    source_block = "\n\n".join(
        f"[{i}] {s['title']} ({s['url']})\n{s['text'][:BRIEF_SOURCE_CHARS]}"
        for i, s in enumerate(sources, 1)
    )
    prompt = (
        f"DOCUMENT SUMMARY ({analysis['title']}):\n{analysis['summary']}\n\n"
        f"KEY POINTS:\n" + "\n".join(f"- {p}" for p in analysis["key_points"]) + "\n\n"
        f"WEB SOURCES:\n{source_block}\n\n"
        "Write a short research brief in Markdown with these three sections, using '- ' for bullets "
        "and citing sources as [1], [2]:\n"
        "**Background from the web** - context that helps understand the document\n"
        "**How it compares** - where the web sources agree with, update, or contradict the document\n"
        "**Worth checking** - open questions or claims to verify\n"
        "Keep it under 300 words. Do not invent facts that are not in the sources."
    )
    try:
        brief = ai_engine.generate_text(prompt, system="You are a careful research assistant.", max_tokens=700)
    except Exception:
        brief = None
    if brief:
        return brief
    return "\n".join(f"- [{i}] {s['snippet'] or s['text'][:200]}" for i, s in enumerate(sources, 1))

def format_report(filename: str, analysis: Dict[str, Any], brief: str, sources: List[Dict[str, Any]], saved: int) -> str:
    report = f"🔎 **Analysis & research complete:** `{filename}`\n\n"
    report += f"### {analysis['title']}\n"
    report += f"*Type: {analysis['document_type']}*\n\n"
    report += f"### Summary\n{analysis['summary']}\n\n"
    if analysis["key_points"]:
        report += "### Key points\n" + "\n".join(f"- {p}" for p in analysis["key_points"]) + "\n\n"
    if analysis["topics"]:
        report += f"**Topics:** {', '.join(analysis['topics'])}\n\n"
    report += f"### Research findings\n{brief}\n\n"
    if sources:
        report += "### Sources\n" + "\n".join(
            f"{i}. [{s['title']}]({s['url']})" for i, s in enumerate(sources, 1)
        ) + "\n\n"
    if not analysis["used_ai"]:
        report += "> ⚠️ *No AI model was reachable, so this analysis is a basic outline. Start Ollama or set a provider in Settings for a full analysis.*\n\n"
    report += f"🧠 *Saved {saved} new knowledge entries (analysis, research brief and web sources). Ask me about this document any time.*"
    return report

def run_document_job(doc_id: int, text: str, filename: str, category: str, session_id: str):
    """Background worker: analyse, research, store, and post the report to the chat."""
    try:
        memory_engine.update_document(doc_id, status="analysing", stage="Analysing the document with AI")
        analysis = analyse_document(text, filename)

        memory_engine.update_document(doc_id, status="researching", stage="Researching the topics on the web")
        research = research_topics(analysis, filename)

        memory_engine.update_document(doc_id, status="writing", stage="Writing the research brief")
        brief = write_research_brief(analysis, research["sources"])

        base_name = os.path.splitext(filename)[0].replace("_", " ").replace("-", " ").title()
        analysis_content = (
            f"Document: {filename}\nTitle: {analysis['title']}\nType: {analysis['document_type']}\n\n"
            f"Summary:\n{analysis['summary']}\n\n"
            "Key points:\n" + "\n".join(f"- {p}" for p in analysis["key_points"]) + "\n\n"
            f"Topics: {', '.join(analysis['topics'])}"
        )
        analysis_mem = memory_engine.add_memory(
            title=f"Analysis: {base_name}",
            content=analysis_content,
            category=category,
            tags=f"analysis, summary, {filename}, {', '.join(analysis['topics'][:4])}",
            source=f"research:{filename}"
        )
        sources_text = "\n".join(f"[{i}] {s['title']} - {s['url']}" for i, s in enumerate(research["sources"], 1))
        brief_mem = memory_engine.add_memory(
            title=f"Research Brief: {base_name}",
            content=f"{brief}\n\nSources:\n{sources_text}",
            category="Research",
            tags=f"research, brief, {filename}, {', '.join(analysis['topics'][:4])}",
            source=f"research:{filename}"
        )

        memories = [analysis_mem, brief_mem] + research["memories"]
        report = format_report(filename, analysis, brief, research["sources"], len(memories))
        memory_ids = [m["id"] for m in memories]
        memory_engine.update_document(
            doc_id, status="done", stage="Complete", result=report, memory_ids=memory_ids
        )
        memory_engine.save_chat_message(session_id, "assistant", report, sources_used=memory_ids)
    except Exception as e:
        message = f"Analysis failed: {e}"
        memory_engine.update_document(doc_id, status="failed", stage="Failed", error=message)
        memory_engine.save_chat_message(
            session_id, "assistant",
            f"⚠️ I stored `{filename}`, but the analysis and research step failed: {e}\n\n"
            "You can still ask questions about the document's contents."
        )

def start_document_job(text: str, filename: str, category: str = "Document", session_id: str = "default") -> int:
    """Registers the document and starts its analysis and research in a background thread."""
    doc_id = memory_engine.create_document(filename, category)
    threading.Thread(
        target=run_document_job,
        args=(doc_id, text, filename, category, session_id),
        daemon=True
    ).start()
    return doc_id
