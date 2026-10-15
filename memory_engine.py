"""
OmniBrain Memory Engine
Handles persistent SQLite storage, FTS5 full-text indexing,
conversational learning detection, and hybrid semantic retrieval.
"""

import sqlite3
import re
import math
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "memory.db")

# Common English stop words for keyword extraction
STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", 
    "aren't", "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", 
    "but", "by", "can", "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does", 
    "doesn't", "doing", "don't", "down", "during", "each", "few", "for", "from", "further", 
    "had", "hadn't", "has", "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", 
    "her", "here", "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i", 
    "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its", 
    "itself", "let's", "me", "more", "most", "mustn't", "my", "myself", "no", "nor", "not", 
    "of", "off", "on", "once", "only", "or", "other", "ought", "our", "ours", "ourselves", "out", 
    "over", "own", "same", "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't", 
    "so", "some", "such", "than", "that", "that's", "the", "their", "theirs", "them", "themselves", 
    "then", "there", "there's", "these", "they", "they'd", "they'll", "they're", "they've", "this", 
    "those", "through", "to", "too", "under", "until", "up", "very", "was", "wasn't", "we", 
    "we'd", "we'll", "we're", "we've", "were", "weren't", "what", "what's", "whatever", "when", 
    "when's", "where", "where's", "which", "while", "who", "who's", "whom", "why", "why's", "with", 
    "won't", "would", "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours", 
    "yourself", "yourselves", "tell", "please", "know", "give", "find", "show", "talk"
}

def get_connection() -> sqlite3.Connection:
    """Creates a database connection with dict-like row access."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database schema with regular tables, FTS5 index, and triggers."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Primary memory table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                category TEXT DEFAULT 'General',
                tags TEXT DEFAULT '',
                source TEXT DEFAULT 'chat',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Virtual table for Full Text Search (FTS5)
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
                content,
                title,
                category,
                tags,
                content='memories',
                content_rowid='id',
                tokenize='porter unicode61'
            )
        """)
        
        # Triggers to keep FTS5 in sync
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
                INSERT INTO memories_fts(rowid, content, title, category, tags)
                VALUES (new.id, new.content, new.title, new.category, new.tags);
            END;
        """)
        
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
                INSERT INTO memories_fts(memories_fts, rowid, content, title, category, tags)
                VALUES ('delete', old.id, old.content, old.title, old.category, old.tags);
            END;
        """)
        
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
                INSERT INTO memories_fts(memories_fts, rowid, content, title, category, tags)
                VALUES ('delete', old.id, old.content, old.title, old.category, old.tags);
                INSERT INTO memories_fts(rowid, content, title, category, tags)
                VALUES (new.id, new.content, new.title, new.category, new.tags);
            END;
        """)
        
        # Chat history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL DEFAULT 'default',
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                sources_used TEXT DEFAULT '[]',
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # App settings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        # Uploaded documents and their background analysis / research jobs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                category TEXT DEFAULT 'Document',
                status TEXT DEFAULT 'queued',
                stage TEXT DEFAULT '',
                result TEXT DEFAULT '',
                error TEXT DEFAULT '',
                memory_ids TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Jobs cannot survive a server restart
        cursor.execute("""
            UPDATE documents SET status = 'failed', error = 'Interrupted by server restart'
            WHERE status NOT IN ('done', 'failed')
        """)

        # Default settings if not present
        default_settings = {
            "ai_provider": "ollama",      # "local", "gemini", "openai", "ollama"
            "gemini_api_key": "",
            "gemini_model": "gemini-2.5-flash",
            "openai_api_key": "",
            "openai_model": "gpt-4o-mini",
            "ollama_model": "llama3.2",
            "ollama_url": "http://localhost:11434",
            "bot_name": "T25-chatbot",
            "auto_speak": "true",
            "speech_rate": "1.0",
            "speech_pitch": "1.0",
            "voice_name": ""
        }
        
        for k, v in default_settings.items():
            cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))
        cursor.execute("UPDATE settings SET value = 'T25-chatbot' WHERE key = 'bot_name'")
            
        conn.commit()

# --- Memory CRUD Operations ---

def add_memory(title: str, content: str, category: str = "General", tags: str = "", source: str = "manual") -> Dict[str, Any]:
    """Adds a new piece of knowledge to the database."""
    title = title.strip()
    content = content.strip()
    category = category.strip() or "General"
    tags = tags.strip()
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO memories (title, content, category, tags, source, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (title, content, category, tags, source))
        conn.commit()
        mem_id = cursor.lastrowid
        
    return get_memory(mem_id)

def update_memory(mem_id: int, title: str, content: str, category: str = "General", tags: str = "") -> Optional[Dict[str, Any]]:
    """Updates an existing memory record."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE memories
            SET title = ?, content = ?, category = ?, tags = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (title.strip(), content.strip(), category.strip(), tags.strip(), mem_id))
        conn.commit()
        if cursor.rowcount == 0:
            return None
    return get_memory(mem_id)

def delete_memory(mem_id: int) -> bool:
    """Deletes a memory record."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM memories WHERE id = ?", (mem_id,))
        conn.commit()
        return cursor.rowcount > 0

def delete_memories_by_source(sources: List[str]) -> int:
    """Deletes every memory whose source exactly matches one of the given values."""
    if not sources:
        return 0
    placeholders = ",".join("?" for _ in sources)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM memories WHERE source IN ({placeholders})", sources)
        conn.commit()
        return cursor.rowcount

def get_memory(mem_id: int) -> Optional[Dict[str, Any]]:
    """Fetches a single memory by ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM memories WHERE id = ?", (mem_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def list_memories(search: str = "", category: str = "", limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """Lists memories with optional filtering and pagination."""
    query = "SELECT * FROM memories WHERE 1=1"
    params = []
    
    if category and category.lower() != "all":
        query += " AND category = ?"
        params.append(category)
        
    if search:
        search_like = f"%{search.strip()}%"
        query += " AND (title LIKE ? OR content LIKE ? OR tags LIKE ?)"
        params.extend([search_like, search_like, search_like])
        
    query += " ORDER BY id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

def get_categories() -> List[str]:
    """Returns a list of distinct categories."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT category FROM memories WHERE category IS NOT NULL AND category != '' ORDER BY category ASC")
        rows = cursor.fetchall()
        cats = [r["category"] for r in rows]
        if "General" not in cats:
            cats.insert(0, "General")
        return cats

def get_stats() -> Dict[str, Any]:
    """Returns database summary statistics."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS total FROM memories")
        total_memories = cursor.fetchone()["total"]
        
        cursor.execute("SELECT COUNT(DISTINCT category) AS total FROM memories")
        total_categories = cursor.fetchone()["total"]
        
        cursor.execute("SELECT COUNT(*) AS total FROM conversations")
        total_messages = cursor.fetchone()["total"]
        
        cursor.execute("SELECT created_at FROM memories ORDER BY id DESC LIMIT 1")
        last_row = cursor.fetchone()
        last_learned = last_row["created_at"] if last_row else None
        
        return {
            "total_memories": total_memories,
            "total_categories": total_categories,
            "total_conversations": total_messages,
            "last_learned": last_learned
        }

def export_all_memories() -> List[Dict[str, Any]]:
    """Exports all stored memories as a clean list for backup."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, content, category, tags, source, created_at FROM memories ORDER BY id ASC")
        return [dict(r) for r in cursor.fetchall()]

def import_memories_data(items: List[Dict[str, Any]]) -> int:
    """Imports an array of knowledge items, skipping empty ones."""
    count = 0
    with get_connection() as conn:
        cursor = conn.cursor()
        for item in items:
            title = (item.get("title") or "Imported Note").strip()
            content = (item.get("content") or "").strip()
            category = (item.get("category") or "General").strip()
            tags = (item.get("tags") or "").strip()
            source = (item.get("source") or "import").strip()
            if content:
                cursor.execute("""
                    INSERT INTO memories (title, content, category, tags, source, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (title, content, category, tags, source))
                count += 1
        conn.commit()
    return count

# --- Smart Hybrid Search & Relevance Engine ---

def extract_tokens(text: str) -> List[str]:
    """Tokenizes text, strips punctuation, normalizes to lowercase."""
    return re.findall(r'\w+', text.lower(), flags=re.UNICODE)

def extract_keywords(text: str) -> List[str]:
    """Extracts meaningful keywords by filtering out common stop words."""
    tokens = extract_tokens(text)
    return [t for t in tokens if t not in STOP_WORDS and len(t) > 1]

def search_relevant_memories(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Retrieves a bounded set of FTS5 candidates and ranks them by relevance.
    """
    clean_query = query.strip()
    if not clean_query:
        return []
        
    keywords = extract_keywords(clean_query)[:12]
    if not keywords:
        return []

    candidates: Dict[int, Dict[str, Any]] = {}
    
    with get_connection() as conn:
        cursor = conn.cursor()
        fts_query = " OR ".join(f'"{keyword}"' for keyword in keywords)
        try:
            cursor.execute("""
                SELECT m.*, bm25(memories_fts) AS bm25_rank
                FROM memories_fts
                JOIN memories m ON memories_fts.rowid = m.id
                WHERE memories_fts MATCH ?
                ORDER BY bm25_rank ASC
                LIMIT 80
            """, (fts_query,))
            rows = cursor.fetchall()
        except sqlite3.OperationalError:
            rows = []

        # Keep a phrase-match fallback for terms FTS tokenization cannot represent.
        if not rows and len(clean_query) > 3:
            cursor.execute("""
                SELECT *, 0.0 AS bm25_rank FROM memories
                WHERE content LIKE ? OR title LIKE ? OR tags LIKE ?
                ORDER BY id DESC LIMIT 80
            """, (f"%{clean_query}%",) * 3)
            rows = cursor.fetchall()

        candidate_count = max(1, len(rows))
        for rank, row in enumerate(rows):
            memory = dict(row)
            title_tokens = set(extract_tokens(memory["title"]))
            content_tokens = set(extract_tokens(
                f"{memory['content']} {memory['category']} {memory.get('tags', '')}"
            ))
            matched = sum(1 for keyword in keywords if keyword in content_tokens or keyword in title_tokens)
            title_matches = sum(1 for keyword in keywords if keyword in title_tokens)
            overlap_score = (matched + title_matches) / (len(keywords) * 2)
            fts_score = (candidate_count - rank) / candidate_count
            phrase_bonus = 0.25 if clean_query.casefold() in (
                f"{memory['title']} {memory['content']}".casefold()
            ) else 0.0
            memory["relevance_score"] = round(fts_score * 0.4 + overlap_score * 0.6 + phrase_bonus, 3)
            candidates[memory["id"]] = memory

    return sorted(
        candidates.values(),
        key=lambda memory: memory["relevance_score"],
        reverse=True
    )[:top_k]

# --- Real-Time Conversational Learning Parser ---

LEARNING_PATTERNS = [
    # "Remember that my phone number is 12345"
    (r'^(?:please\s+)?(?:remember|learn|store|memorize|save|note down|record|keep in mind)(?:\s+that)?(?:\s*:\s*|\s+)(.+)$', 1),
    # "Note that the meeting is on Friday"
    (r'^(?:note\s+that|take note that)(?:\s*:\s*|\s+)(.+)$', 1),
    # "My [attribute] is [value]"
    (r'^(my\s+(?:name|email|phone|address|birthday|hobby|job|role|favorite\s+\w+|wife|husband|pet|dog|cat|project|car|password))\s+(?:is|are|=|:)\s+(.+)$', 0),
    # "Fact: The Earth orbits the Sun"
    (r'^(?:fact|info|note|knowledge|data)\s*:\s*(.+)$', 1),
    # "Title: X | Content: Y" or "Title: X \n Content: Y"
    (r'^title\s*:\s*([^\n|]+)(?:[\n|]\s*content\s*:\s*)(.+)$', 'custom')
]

def auto_detect_category(title: str, content: str) -> str:
    """Heuristic categorizer for new memories."""
    text = (title + " " + content).lower()
    if any(w in text for w in ["my name", "my email", "my phone", "my birthday", "my pet", "i live", "i like", "my favorite"]):
        return "Personal"
    elif any(w in text for w in ["meeting", "project", "deadline", "client", "office", "company", "boss", "task", "work"]):
        return "Work"
    elif any(w in text for w in ["password", "credential", "api key", "pin", "login", "secret", "token"]):
        return "Credentials"
    elif any(w in text for w in ["how to", "guide", "tutorial", "instruction", "steps"]):
        return "Guides"
    elif any(w in text for w in ["defined as", "history", "scientific", "fact", "discovered", "invented"]):
        return "Facts"
    return "General"

def generate_title_from_content(content: str) -> str:
    """Generates a concise, human-readable title from statement content."""
    # Check for "my X is Y"
    match = re.search(r'my\s+([\w\s]{2,25}?)\s+(?:is|are)\s+', content, re.IGNORECASE)
    if match:
        attr = match.group(1).strip()
        return f"User's {attr.capitalize()}"
        
    # Check for "[Subject] is/was/has"
    match = re.search(r'^([A-Z][\w\s]{2,30}?)\s+(?:is|was|are|has|belongs)\s+', content)
    if match:
        return match.group(1).strip()
        
    # Clean first sentence or words
    words = content.strip().split()
    if len(words) <= 6:
        return content.strip().rstrip('.!')
    first_chunk = " ".join(words[:6])
    return first_chunk + "..."

def detect_and_learn_from_message(message: str) -> Optional[Dict[str, Any]]:
    """
    Analyzes the user's chat message. If it represents an intent to teach
    or store knowledge, extracts the data, saves it to memory, and returns
    the created memory along with a confirmation message.
    """
    clean_msg = message.strip()
    
    # Check Title: ... Content: ...
    custom_match = re.search(r'^title\s*:\s*([^\n|]+)(?:[\n|]\s*content\s*:\s*)(.+)$', clean_msg, re.IGNORECASE | re.DOTALL)
    if custom_match:
        title = custom_match.group(1).strip()
        content = custom_match.group(2).strip()
        cat = auto_detect_category(title, content)
        mem = add_memory(title=title, content=content, category=cat, source="chat")
        return {
            "learned": True,
            "memory": mem,
            "response": f"🧠 I've saved that into my memory under **{cat}**!\n- **Title:** {title}\n- **Content:** {content}"
        }
        
    for pattern, group_mode in LEARNING_PATTERNS:
        match = re.search(pattern, clean_msg, re.IGNORECASE)
        if match:
            if group_mode == 0:
                # "my phone is 123"
                attr = match.group(1).strip()
                val = match.group(2).strip()
                content = f"{attr.capitalize()} is {val}."
                title = f"{attr.capitalize()}"
            elif group_mode == 1:
                content = match.group(1).strip()
                title = generate_title_from_content(content)
            else:
                continue
                
            cat = auto_detect_category(title, content)
            mem = add_memory(title=title, content=content, category=cat, source="chat")
            return {
                "learned": True,
                "memory": mem,
                "response": f"🧠 Got it! I've learned and saved this to my memory under **{cat}**:\n> *\"{content}\"*\n\nYou can ask me about this anytime via chat or voice!"
            }
            
    return None

# --- Conversation History Management ---

def save_chat_message(session_id: str, role: str, content: str, sources_used: List[Any] = None) -> int:
    """Stores a message in the conversation history."""
    sources_json = json.dumps(sources_used or [])
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO conversations (session_id, role, content, sources_used, timestamp)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (session_id, role, content, sources_json))
        conn.commit()
        return cursor.lastrowid

def get_chat_history(session_id: str = "default", limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieves previous chat messages for the session."""
    with get_connection() as conn:
        cursor = conn.cursor()
        # Most recent messages, returned oldest-first
        cursor.execute("""
            SELECT * FROM (
                SELECT id, session_id, role, content, sources_used, timestamp
                FROM conversations
                WHERE session_id = ?
                ORDER BY id DESC
                LIMIT ?
            ) ORDER BY id ASC
        """, (session_id, limit))
        rows = cursor.fetchall()
        history = []
        for r in rows:
            item = dict(r)
            try:
                item["sources_used"] = json.loads(item.get("sources_used", "[]"))
            except Exception:
                item["sources_used"] = []
            history.append(item)
        return history

def clear_chat_history(session_id: str = "default") -> bool:
    """Clears conversation messages for a session."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM conversations WHERE session_id = ?", (session_id,))
        conn.commit()
        return True

# --- Document Analysis Jobs ---

def create_document(filename: str, category: str = "Document") -> int:
    """Registers an uploaded document whose analysis is about to start."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO documents (filename, category, status, stage) VALUES (?, ?, 'queued', 'Waiting to start')",
            (filename, category)
        )
        conn.commit()
        return cursor.lastrowid

def update_document(doc_id: int, **fields: Any):
    """Updates status, stage, result, error, or memory_ids of a document job."""
    allowed = {"status", "stage", "result", "error", "memory_ids"}
    updates = {k: (json.dumps(v) if k == "memory_ids" else v) for k, v in fields.items() if k in allowed}
    if not updates:
        return
    assignments = ", ".join(f"{k} = ?" for k in updates)
    with get_connection() as conn:
        conn.execute(
            f"UPDATE documents SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            [*updates.values(), doc_id]
        )
        conn.commit()

def get_document(doc_id: int) -> Optional[Dict[str, Any]]:
    """Fetches a single document job by ID."""
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
    if not row:
        return None
    item = dict(row)
    item["memory_ids"] = json.loads(item.get("memory_ids") or "[]")
    return item

def list_documents(limit: int = 100) -> List[Dict[str, Any]]:
    """Lists uploaded documents, newest first, without the full result text."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, filename, category, status, stage, error, created_at, updated_at "
            "FROM documents ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
    return [dict(r) for r in rows]

# --- App Settings Store ---

def get_setting(key: str, default: str = "") -> str:
    """Retrieves a configuration setting."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row["value"] if row else default

def set_setting(key: str, value: str):
    """Sets a configuration setting."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
        conn.commit()

def get_all_settings() -> Dict[str, str]:
    """Returns all configuration settings."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM settings")
        return {r["key"]: r["value"] for r in cursor.fetchall()}
