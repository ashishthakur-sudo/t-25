"""
OmniBrain FastAPI Application
Exposes RESTful endpoints for chat, memory management, document ingestion,
voice settings, and serves the Single-Page Web Application.
"""

import os
import json
import io
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import memory_engine
import ai_engine
import extractor_engine

app = FastAPI(title="T25-chatbot API", version="1.0.0")

# Enable CORS for local cross-origin development if needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database tables on startup
@app.on_event("startup")
def startup_event():
    memory_engine.init_db()

# --- Request / Response Models ---

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"

class MemoryCreateRequest(BaseModel):
    title: str
    content: str
    category: str = "General"
    tags: str = ""

class MemoryUpdateRequest(BaseModel):
    title: str
    content: str
    category: str = "General"
    tags: str = ""

# --- Chat Endpoints ---

@app.post("/api/chat")
def handle_chat(payload: ChatRequest):
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    result = ai_engine.process_user_message(payload.message, session_id=payload.session_id)
    return result

@app.get("/api/chat/history")
def get_history(session_id: str = "default", limit: int = 50):
    history = memory_engine.get_chat_history(session_id=session_id, limit=limit)
    return {"history": history}

@app.post("/api/chat/clear")
def clear_history(session_id: str = "default"):
    memory_engine.clear_chat_history(session_id=session_id)
    return {"success": True, "message": "Chat history cleared"}

# --- Knowledge Base / Memories Endpoints ---

@app.get("/api/memories")
def list_memories(search: str = "", category: str = "", limit: int = 100, offset: int = 0):
    items = memory_engine.list_memories(search=search, category=category, limit=limit, offset=offset)
    categories = memory_engine.get_categories()
    stats = memory_engine.get_stats()
    return {
        "memories": items,
        "categories": categories,
        "stats": stats
    }

@app.post("/api/memories")
def create_memory(item: MemoryCreateRequest):
    if not item.title.strip() or not item.content.strip():
        raise HTTPException(status_code=400, detail="Title and content are required")
    created = memory_engine.add_memory(
        title=item.title,
        content=item.content,
        category=item.category,
        tags=item.tags,
        source="manual"
    )
    return created

@app.put("/api/memories/{mem_id}")
def update_memory_item(mem_id: int, item: MemoryUpdateRequest):
    updated = memory_engine.update_memory(
        mem_id=mem_id,
        title=item.title,
        content=item.content,
        category=item.category,
        tags=item.tags
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Memory item not found")
    return updated

@app.delete("/api/memories/{mem_id}")
def delete_memory_item(mem_id: int):
    success = memory_engine.delete_memory(mem_id)
    if not success:
        raise HTTPException(status_code=404, detail="Memory item not found")
    return {"success": True, "message": "Memory item deleted"}

@app.get("/api/memories/export")
def export_memories_endpoint():
    data = memory_engine.export_all_memories()
    return JSONResponse(
        content=data,
        headers={"Content-Disposition": "attachment; filename=cognibot_memories_export.json"}
    )

@app.post("/api/memories/import")
def import_memories_endpoint(items: List[Dict[str, Any]]):
    count = memory_engine.import_memories_data(items)
    return {"success": True, "imported_count": count}

class UrlExtractRequest(BaseModel):
    url: str
    session_id: str = "default"

@app.post("/api/extract/url")
def extract_url_endpoint(payload: UrlExtractRequest):
    if not payload.url.strip():
        raise HTTPException(status_code=400, detail="URL cannot be empty")
    res = extractor_engine.fetch_and_extract_url(payload.url)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Failed to fetch URL"))
    
    memory_engine.save_chat_message(
        session_id=payload.session_id,
        role="assistant",
        content=res["display_message"],
        sources_used=[m["id"] for m in res.get("memories", [])]
    )
    return res

# --- File Ingestion (PDFs, Images, Documents) ---

@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...), category: str = Form("Document")):
    filename = file.filename or "uploaded_file.txt"
    contents = await file.read()
    ext = os.path.splitext(filename)[1].lower()

    # 1. Handle PDF
    if ext == ".pdf":
        result = extractor_engine.extract_and_store_pdf(contents, filename, category=category)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to process PDF"))
        return {
            "success": True,
            "filename": filename,
            "chunks_stored": result.get("chunks_stored", 0),
            "message": result.get("display_message"),
            "speech_text": result.get("speech_text")
        }

    # 2. Handle Images
    if ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"]:
        result = extractor_engine.analyze_and_process_image(contents, filename)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to process image"))
        return {
            "success": True,
            "filename": filename,
            "image_url": result.get("image_url"),
            "message": result.get("analysis"),
            "speech_text": result.get("speech_text"),
            "chunks_stored": 1
        }

    # 3. Handle Text Documents (txt, md, csv, json)
    try:
        text = contents.decode("utf-8", errors="replace")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file as text: {str(e)}")
        
    if not text.strip():
        raise HTTPException(status_code=400, detail="File is empty")
        
    chunks = extractor_engine.chunk_text(text, chunk_size=800)
    created_items = []
    base_name = os.path.splitext(filename)[0].replace("_", " ").replace("-", " ").title()
    
    for idx, p in enumerate(chunks, 1):
        title = f"{base_name} (Section {idx})" if len(chunks) > 1 else base_name
        mem = memory_engine.add_memory(
            title=title,
            content=p,
            category=category,
            tags=filename,
            source=f"upload:{filename}"
        )
        created_items.append(mem)
        
    return {
        "success": True,
        "filename": filename,
        "chunks_stored": len(created_items),
        "message": f"Successfully learned and stored {len(created_items)} sections from '{filename}'",
        "speech_text": f"Successfully ingested {filename} and stored {len(created_items)} sections in memory."
    }

# --- Chat Attachment (Direct upload & question from Chat Bar) ---

@app.post("/api/chat/attachment")
async def chat_attachment(
    file: UploadFile = File(...),
    message: str = Form(""),
    session_id: str = Form("default")
):
    filename = file.filename or "attachment"
    contents = await file.read()
    ext = os.path.splitext(filename)[1].lower()
    
    user_label = f"Attached: `{filename}`" + (f"\n\n{message}" if message.strip() else "")
    memory_engine.save_chat_message(session_id=session_id, role="user", content=user_label)
    
    # Process PDF
    if ext == ".pdf":
        res = extractor_engine.extract_and_store_pdf(contents, filename)
        if not res.get("success"):
            raise HTTPException(status_code=400, detail=res.get("error"))
        bot_reply = res["display_message"]
        speech_text = res["speech_text"]
        memory_engine.save_chat_message(
            session_id=session_id,
            role="assistant",
            content=bot_reply,
            sources_used=[m["id"] for m in res.get("memories", [])]
        )
        return {
            "text": bot_reply,
            "speech_text": speech_text,
            "sources": res.get("memories", []),
            "learned": True
        }
        
    # Process Image
    if ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"]:
        res = extractor_engine.analyze_and_process_image(contents, filename, user_prompt=message)
        if not res.get("success"):
            raise HTTPException(status_code=400, detail=res.get("error"))
        img_tag = f"![{filename}]({res['image_url']})\n\n"
        bot_reply = img_tag + res["analysis"]
        speech_text = res["speech_text"]
        memory_engine.save_chat_message(
            session_id=session_id,
            role="assistant",
            content=bot_reply,
            sources_used=[res["memory"]["id"]] if res.get("memory") else []
        )
        return {
            "text": bot_reply,
            "speech_text": speech_text,
            "sources": [res["memory"]] if res.get("memory") else [],
            "learned": True,
            "image_url": res["image_url"]
        }
        
    # Process Text/Doc
    try:
        text = contents.decode("utf-8", errors="replace")
        chunks = extractor_engine.chunk_text(text, chunk_size=800)
        base_name = os.path.splitext(filename)[0].replace("_", " ").title()
        stored = []
        for idx, ch in enumerate(chunks, 1):
            m = memory_engine.add_memory(
                title=f"{base_name} (Section {idx})",
                content=ch,
                category="Document",
                tags=filename,
                source=f"upload:{filename}"
            )
            stored.append(m)
        bot_reply = (
            f"📄 **Document `{filename}` Ingested:**\n\n"
            f"> Stored {len(stored)} sections into memory.\n\n"
            f"🧠 *Ask me any questions about `{filename}`!*"
        )
        speech_text = f"Successfully learned {filename} and stored {len(stored)} sections into memory."
        memory_engine.save_chat_message(
            session_id=session_id,
            role="assistant",
            content=bot_reply,
            sources_used=[m["id"] for m in stored]
        )
        return {
            "text": bot_reply,
            "speech_text": speech_text,
            "sources": stored,
            "learned": True
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process file: {str(e)}")

# --- Settings & Stats Endpoints ---

@app.get("/api/settings")
def get_settings_endpoint():
    settings = memory_engine.get_all_settings()
    # Mask API keys in UI display for security
    masked = dict(settings)
    if masked.get("gemini_api_key"):
        k = masked["gemini_api_key"]
        masked["gemini_api_key_masked"] = f"••••••••{k[-4:]}" if len(k) > 4 else "••••"
    if masked.get("openai_api_key"):
        k = masked["openai_api_key"]
        masked["openai_api_key_masked"] = f"••••••••{k[-4:]}" if len(k) > 4 else "••••"
    return masked

@app.post("/api/settings")
def update_settings_endpoint(settings: Dict[str, str]):
    for k, v in settings.items():
        if k in ["gemini_api_key", "openai_api_key"] and v.startswith("••••"):
            continue  # do not overwrite masked placeholder
        memory_engine.set_setting(k, v)
    return {"success": True, "message": "Settings updated"}

@app.get("/api/stats")
def get_stats_endpoint():
    return memory_engine.get_stats()

# --- Serve Single-Page Frontend ---

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def serve_index():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "CogniBot API is running. static/index.html not found."}
