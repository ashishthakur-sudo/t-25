"""
OmniBrain Extractor & Web Engine
Handles:
1. Web Scraping & Product/Article Information Extraction (JSON-LD, OpenGraph, DOM)
2. PDF text extraction & chunking for long articles/books (pypdf)
3. Image processing & multimodal visual analysis (Pillow + Gemini Vision)
"""

import os
import re
import json
import base64
import requests
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup
from docx import Document
from openpyxl import load_workbook
from pypdf import PdfReader
from io import BytesIO
from PIL import Image
from pptx import Presentation

import memory_engine
from ai_engine import clean_for_speech, call_gemini_api

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

def chunk_text(text: str, chunk_size: int = 800, overlap: int = 150) -> List[str]:
    """Splits long text into overlapping chunks for semantic retrieval."""
    clean_text = text.strip()
    if not clean_text:
        return []

    chunk_size = max(1, chunk_size)
    overlap = min(max(0, overlap), chunk_size - 1)
    chunks = []
    start = 0
    while start < len(clean_text):
        end = min(start + chunk_size, len(clean_text))
        if end < len(clean_text):
            split_floor = start + chunk_size // 2
            boundary = max(clean_text.rfind("\n", split_floor, end), clean_text.rfind(" ", split_floor, end))
            if boundary > start:
                end = boundary
        chunk = clean_text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(clean_text):
            break
        start = max(start + 1, end - overlap)

    return chunks

def extract_document_text(file_bytes: bytes, filename: str) -> str:
    """Extracts searchable text from supported document and source formats."""
    extension = os.path.splitext(filename)[1].lower()

    if extension == ".docx":
        document = Document(BytesIO(file_bytes))
        sections = [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()]
        for table in document.tables:
            sections.extend(" | ".join(cell.text.strip() for cell in row.cells) for row in table.rows)
        return "\n\n".join(sections)

    if extension == ".xlsx":
        workbook = load_workbook(BytesIO(file_bytes), read_only=True, data_only=True)
        sections = []
        try:
            for sheet in workbook.worksheets:
                sections.append(f"Sheet: {sheet.title}")
                for row in sheet.iter_rows(values_only=True):
                    values = [str(value).strip() for value in row if value is not None and str(value).strip()]
                    if values:
                        sections.append(" | ".join(values))
        finally:
            workbook.close()
        return "\n".join(sections)

    if extension == ".pptx":
        presentation = Presentation(BytesIO(file_bytes))
        sections = []
        for slide_number, slide in enumerate(presentation.slides, 1):
            sections.append(f"Slide {slide_number}")
            for shape in slide.shapes:
                if shape.has_text_frame and shape.text.strip():
                    sections.append(shape.text.strip())
                if shape.has_table:
                    for row in shape.table.rows:
                        sections.append(" | ".join(cell.text.strip() for cell in row.cells))
        return "\n\n".join(sections)

    if extension in {".html", ".htm"}:
        soup = BeautifulSoup(file_bytes, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "noscript"]):
            tag.decompose()
        return soup.get_text("\n", strip=True)

    text_extensions = {
        ".txt", ".md", ".csv", ".json", ".xml", ".yaml", ".yml", ".log",
        ".rst", ".ini", ".cfg", ".py", ".js", ".css"
    }
    if extension in text_extensions:
        return file_bytes.decode("utf-8-sig")

    raise ValueError(f"Unsupported file type '{extension or 'unknown'}'. Upload PDF, image, DOCX, XLSX, PPTX, HTML, or a text file.")

def store_document_text(text: str, filename: str, category: str = "Document") -> Dict[str, Any]:
    """Chunks extracted document text and stores each section in searchable memory."""
    if not text.strip():
        raise ValueError(f"No readable text was found in '{filename}'.")

    # Re-uploading the same file replaces its earlier sections, analysis and research
    memory_engine.delete_memories_by_source([f"upload:{filename}", f"research:{filename}"])
    chunks = chunk_text(text, chunk_size=800)
    base_name = os.path.splitext(filename)[0].replace("_", " ").replace("-", " ").title()
    memories = []
    for index, chunk in enumerate(chunks, 1):
        title = f"{base_name} (Section {index})" if len(chunks) > 1 else base_name
        memories.append(memory_engine.add_memory(
            title=title,
            content=chunk,
            category=category,
            tags=filename,
            source=f"upload:{filename}"
        ))

    return {
        "success": True,
        "filename": filename,
        "chunks_stored": len(memories),
        "memories": memories,
        "text": text,
        "message": f"Successfully learned and stored {len(memories)} sections from '{filename}'",
        "speech_text": f"Successfully ingested {filename} and stored {len(memories)} sections in memory."
    }

def extract_and_store_document(file_bytes: bytes, filename: str, category: str = "Document") -> Dict[str, Any]:
    """Extracts a supported non-PDF document and indexes it in local memory."""
    return store_document_text(extract_document_text(file_bytes, filename), filename, category)

# --- 1. Web Page & Product Extractor ---

def fetch_and_extract_url(url: str) -> Dict[str, Any]:
    """
    Fetches a web page URL and extracts:
    - E-commerce Product Information (price, currency, rating, availability, brand)
    - Long Article & News Content
    - Meta tags and structured schema
    Stores all extracted knowledge in memory and returns a rich summary.
    """
    clean_url = url.strip()
    if not clean_url.startswith(("http://", "https://")):
        clean_url = "https://" + clean_url

    try:
        resp = requests.get(clean_url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to access URL: {str(e)}",
            "url": clean_url
        }

    soup = BeautifulSoup(resp.text, "html.parser")
    
    # 1. Extract Title
    title = ""
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        title = og_title["content"].strip()
    elif soup.title and soup.title.string:
        title = soup.title.string.strip()
    elif soup.find("h1"):
        title = soup.find("h1").get_text(strip=True)
    else:
        title = clean_url

    # 2. Extract OpenGraph Image & Description
    image_url = ""
    og_image = soup.find("meta", property="og:image")
    if og_image and og_image.get("content"):
        image_url = og_image["content"].strip()
        
    og_desc = soup.find("meta", property="og:description")
    description = og_desc["content"].strip() if og_desc and og_desc.get("content") else ""

    # 3. Check for Schema.org JSON-LD (Product, Article, NewsArticle)
    product_data = None
    article_data = None
    
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            raw_json = script.string
            if not raw_json:
                continue
            data = json.loads(raw_json)
            # Could be list or single object or @graph
            items = []
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                items = data.get("@graph", [data])
                
            for item in items:
                if not isinstance(item, dict):
                    continue
                itype = str(item.get("@type", "")).lower()
                if "product" in itype:
                    product_data = item
                elif any(a in itype for a in ["article", "newsarticle", "blogposting"]):
                    article_data = item
        except Exception:
            continue

    is_product = product_data is not None
    price_str = None
    currency_str = None
    brand_str = None
    rating_str = None
    availability_str = None

    if product_data:
        title = product_data.get("name") or title
        description = product_data.get("description") or description
        
        # Brand
        brand_val = product_data.get("brand")
        if isinstance(brand_val, dict):
            brand_str = brand_val.get("name")
        elif isinstance(brand_val, str):
            brand_str = brand_val
            
        # Offers / Price
        offers = product_data.get("offers")
        if isinstance(offers, list) and offers:
            offers = offers[0]
        if isinstance(offers, dict):
            price_str = str(offers.get("price", ""))
            currency_str = str(offers.get("priceCurrency", ""))
            avail = str(offers.get("availability", ""))
            if "InStock" in avail:
                availability_str = "In Stock"
            elif "OutOfStock" in avail:
                availability_str = "Out of Stock"
                
        # Rating
        rating_obj = product_data.get("aggregateRating")
        if isinstance(rating_obj, dict):
            val = rating_obj.get("ratingValue")
            count = rating_obj.get("reviewCount") or rating_obj.get("ratingCount")
            if val:
                rating_str = f"⭐ {val}/5" + (f" ({count} reviews)" if count else "")

    # 4. Fallback Heuristics for Product prices in HTML
    if not price_str:
        # Check OpenGraph price
        og_price = soup.find("meta", property="product:price:amount") or soup.find("meta", property="og:price:amount")
        if og_price and og_price.get("content"):
            price_str = og_price["content"].strip()
            og_cur = soup.find("meta", property="product:price:currency") or soup.find("meta", property="og:price:currency")
            currency_str = og_cur["content"].strip() if og_cur and og_cur.get("content") else "$"
            is_product = True
            
    if not price_str:
        # Common price selectors: .price, .product-price, [itemprop='price']
        price_elem = soup.find(attrs={"itemprop": "price"}) or soup.find(class_=re.compile(r'\b(product-price|price-current|current-price|price)\b', re.I))
        if price_elem:
            p_text = price_elem.get_text(strip=True)
            if any(c in p_text for c in ["$", "€", "£", "₹", "¥"]):
                price_str = p_text
                is_product = True

    # 5. Extract readable article/body text
    # Remove navigation, scripts, footer, header
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg", "aside"]):
        tag.decompose()
        
    # Get paragraphs
    paragraphs = []
    main_elem = soup.find("article") or soup.find("main") or soup.find(id=re.compile(r'content|main|article', re.I)) or soup.body
    if main_elem:
        for p in main_elem.find_all(["p", "h2", "h3", "li", "tr", "blockquote", "dt", "dd"]):
            separator = " | " if p.name == "tr" else " "
            text_line = p.get_text(separator, strip=True)
            if len(text_line) > 25:
                paragraphs.append(text_line)
                
    full_body_text = "\n\n".join(paragraphs) if paragraphs else (description or soup.get_text(" ", strip=True)[:4000])

    # 6. Chunk and Store into Memory
    category = "Products" if is_product else "Web Articles"
    chunks = chunk_text(full_body_text, chunk_size=800)
    
    stored_memories = []
    
    # Store primary overview card
    summary_content = ""
    if is_product:
        summary_content = f"**Product Name:** {title}\n"
        if brand_str:
            summary_content += f"- **Brand:** {brand_str}\n"
        if price_str:
            curr = (currency_str or "$") if not price_str.startswith(("$", "€", "£", "₹", "¥")) else ""
            summary_content += f"- **Price:** {curr}{price_str}\n"
        if availability_str:
            summary_content += f"- **Availability:** {availability_str}\n"
        if rating_str:
            summary_content += f"- **Rating:** {rating_str}\n"
        summary_content += f"- **URL:** {clean_url}\n\n"
        if description:
            summary_content += f"**Description:**\n{description[:600]}\n"
    else:
        summary_content = f"**Article:** {title}\n- **Source:** {clean_url}\n\n"
        summary_content += f"**Key Excerpt / Summary:**\n{description or (full_body_text[:500] + '...')}\n"

    # Store master overview
    overview_mem = memory_engine.add_memory(
        title=f"Overview: {title[:60]}",
        content=summary_content,
        category=category,
        tags=f"web, {clean_url}",
        source=f"url:{clean_url}"
    )
    stored_memories.append(overview_mem)

    # Store remaining long chunks
    for idx, ch in enumerate(chunks, 1):
        if len(ch) > 40:
            m = memory_engine.add_memory(
                title=f"{title[:45]} (Part {idx})",
                content=ch,
                category=category,
                tags=f"web, {clean_url}",
                source=f"url:{clean_url}"
            )
            stored_memories.append(m)

    # Format user-facing message & speech
    if is_product:
        display_msg = (
            f"🛒 **Product Information Extracted & Saved:**\n\n"
            f"### {title}\n"
            f"- **Price:** **{(currency_str or '$') if price_str and not price_str.startswith(('$', '€', '£', '₹', '¥')) else ''}{price_str or 'Not listed'}**\n"
        )
        if brand_str:
            display_msg += f"- **Brand:** {brand_str}\n"
        if availability_str:
            display_msg += f"- **Status:** {availability_str}\n"
        if rating_str:
            display_msg += f"- **Rating:** {rating_str}\n"
        display_msg += f"- **Source Link:** [{clean_url}]({clean_url})\n\n"
        if description:
            display_msg += f"> {description[:400]}{'...' if len(description) > 400 else ''}\n\n"
        display_msg += f"🧠 *Indexed {len(stored_memories)} knowledge sections into memory. You can ask me any questions about this product!*"
        
        speech_text = f"I fetched the product information for {title}. Price is {price_str or 'not specified'}, and it has been saved to your memory."
    else:
        display_msg = (
            f"🌐 **Website Content & Article Saved:**\n\n"
            f"### {title}\n"
            f"- **URL:** [{clean_url}]({clean_url})\n"
            f"- **Sections Stored:** {len(stored_memories)} knowledge chunks\n\n"
            f"> {description or full_body_text[:350]}...\n\n"
            f"🧠 *The entire article has been learned and stored. Ask me anything to summarize or find specific details!*"
        )
        speech_text = f"I fetched and learned the article {title}. I stored {len(stored_memories)} sections into memory. You can ask me any questions about it."

    return {
        "success": True,
        "is_product": is_product,
        "title": title,
        "url": clean_url,
        "price": price_str,
        "brand": brand_str,
        "rating": rating_str,
        "image_url": image_url,
        "chunks_stored": len(stored_memories),
        "display_message": display_msg,
        "speech_text": speech_text,
        "memories": stored_memories
    }

# --- 2. PDF & Long Article Extractor ---

def extract_and_store_pdf(file_bytes: bytes, filename: str, category: str = "PDF Document") -> Dict[str, Any]:
    """
    Extracts text from all pages of a PDF document using pypdf,
    chunks long text systematically, and stores it in memory.
    """
    try:
        reader = PdfReader(BytesIO(file_bytes))
        total_pages = len(reader.pages)
        
        page_texts = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text and text.strip():
                page_texts.append(f"--- [Page {i + 1}] ---\n{text.strip()}")
                
        if not page_texts:
            return {
                "success": False,
                "error": "The PDF does not contain extractable text (it might be scanned images)."
            }
            
        full_pdf_text = "\n\n".join(page_texts)
        chunks = chunk_text(full_pdf_text, chunk_size=900)

        # Re-uploading the same file replaces its earlier sections, analysis and research
        memory_engine.delete_memories_by_source([f"pdf:{filename}", f"research:{filename}"])
        
        base_name = os.path.splitext(filename)[0].replace("_", " ").replace("-", " ").title()
        
        stored_memories = []
        
        # Primary summary overview
        first_page_excerpt = page_texts[0][:600] if page_texts else ""
        overview_content = (
            f"**PDF Document:** {filename}\n"
            f"- **Total Pages:** {total_pages}\n"
            f"- **Total Chunks:** {len(chunks)}\n\n"
            f"**Opening Excerpt:**\n{first_page_excerpt}..."
        )
        
        overview_mem = memory_engine.add_memory(
            title=f"Overview: {base_name}",
            content=overview_content,
            category=category,
            tags=f"pdf, {filename}",
            source=f"pdf:{filename}"
        )
        stored_memories.append(overview_mem)
        
        # Index all remaining chunks
        for idx, ch in enumerate(chunks, 1):
            m = memory_engine.add_memory(
                title=f"{base_name} (Section {idx})",
                content=ch,
                category=category,
                tags=f"pdf, {filename}",
                source=f"pdf:{filename}"
            )
            stored_memories.append(m)
            
        display_msg = (
            f"📄 **PDF Processed & Stored in Memory:**\n\n"
            f"### {base_name}\n"
            f"- **Filename:** `{filename}`\n"
            f"- **Pages Processed:** {total_pages}\n"
            f"- **Knowledge Chunks Stored:** {len(stored_memories)}\n\n"
            f"**Preview:**\n> {first_page_excerpt[:350]}...\n\n"
            f"🧠 *All {total_pages} pages have been indexed into your personal Knowledge Base. You can now ask questions about any topic in this document!*"
        )
        
        speech_text = f"Successfully parsed {filename}. I stored {total_pages} pages and {len(stored_memories)} knowledge sections into memory. You can ask me questions about it anytime."
        
        return {
            "success": True,
            "filename": filename,
            "total_pages": total_pages,
            "chunks_stored": len(stored_memories),
            "display_message": display_msg,
            "speech_text": speech_text,
            "memories": stored_memories,
            "text": full_pdf_text
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to process PDF: {str(e)}"
        }

# --- 3. Image Processing & Vision Extractor ---

def analyze_and_process_image(file_bytes: bytes, filename: str, user_prompt: str = "") -> Dict[str, Any]:
    """
    Saves the image, extracts dimensions and EXIF metadata,
    and runs visual analysis using Gemini Vision (if configured)
    or local image analyzer.
    """
    try:
        # Save image locally so it can be viewed in chat
        clean_filename = f"img_{int(os.path.getmtime(UPLOAD_DIR) if os.path.exists(UPLOAD_DIR) else 0)}_{filename}"
        clean_filename = re.sub(r'[^a-zA-Z0-9_\.-]', '_', clean_filename)
        save_path = os.path.join(UPLOAD_DIR, clean_filename)
        
        with open(save_path, "wb") as f:
            f.write(file_bytes)
            
        img = Image.open(BytesIO(file_bytes))
        width, height = img.size
        img_format = img.format or "JPEG"
        
        # Prepare base64 for vision API
        b64_image = base64.b64encode(file_bytes).decode("utf-8")
        mime_type = f"image/{img_format.lower()}"
        if mime_type == "image/jpg":
            mime_type = "image/jpeg"
            
        provider = memory_engine.get_setting("ai_provider", "local")
        gemini_key = memory_engine.get_setting("gemini_api_key", "").strip()
        gemini_model = memory_engine.get_setting("gemini_model", "gemini-1.5-flash").strip()
        
        analysis_text = ""
        
        # Multimodal Gemini Vision if key available
        if gemini_key:
            prompt = user_prompt.strip() or (
                "Analyze this image in detail. "
                "1. If it contains a product or items, describe the product, brand, features, and details. "
                "2. If it contains text, documents, or receipts, transcribe the key text accurately. "
                "3. If it is a diagram, chart, or scene, explain what it shows. "
                "Provide a helpful, well-structured response."
            )
            
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent?key={gemini_key}"
            payload = {
                "contents": [{
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": b64_image
                            }
                        }
                    ]
                }]
            }
            try:
                r = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=25)
                r.raise_for_status()
                res_data = r.json()
                analysis_text = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
            except Exception as e:
                analysis_text = f"Image saved. (Vision API error: {str(e)})"
        else:
            # Local Offline description
            analysis_text = (
                f"🖼️ **Image Received & Saved**\n\n"
                f"- **Filename:** `{filename}`\n"
                f"- **Resolution:** {width} x {height} pixels\n"
                f"- **Format:** {img_format}\n\n"
                f"💡 *Tip: Connect your Google Gemini API key in the **Settings** tab for instant AI visual description, OCR text transcription, and product analysis!*"
            )

        # Store in knowledge base
        base_name = os.path.splitext(filename)[0].replace("_", " ").title()
        mem = memory_engine.add_memory(
            title=f"Image: {base_name}",
            content=f"Image File: {clean_filename}\nResolution: {width}x{height}\nAnalysis:\n{analysis_text}",
            category="Images",
            tags=f"image, {filename}",
            source=f"image:{clean_filename}"
        )
        
        speech_text = clean_for_speech(analysis_text)
        
        return {
            "success": True,
            "filename": filename,
            "image_url": f"/static/uploads/{clean_filename}",
            "analysis": analysis_text,
            "speech_text": speech_text,
            "memory": mem
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to process image: {str(e)}"
        }
