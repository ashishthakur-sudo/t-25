# 🧠 T25-chatbot — Adaptive Learning, Multimodal & Voice AI Companion

An intelligent personal AI chatbot that can **learn in real-time**, **extract & store data from images, PDFs, long articles, and website links**, and **answer questions via text chat or spoken voice**.

---

## ✨ Upgraded Capabilities

### 1. 🖼️ Image Support (Vision & OCR)
- Attach photos, screenshots, receipts, or diagrams via the 📎 attachment button in the chat bar or drag-and-drop.
- **Multimodal Analysis:** Displays the image directly in the chat, stores it in memory, and explains or transcribes the visual information.
- Optional Google Gemini Vision integration for advanced OCR, diagram breakdown, and product recognition.

### 2. 📄 Documents, Spreadsheets & Presentations
- Upload PDF, DOCX, XLSX, PPTX, HTML, Markdown, CSV, JSON, and other supported text files.
- Extracts text from document paragraphs, spreadsheet rows, presentation slides, and web-page tables, then indexes every section in persistent SQLite memory.
- Ask a question in the same message as an attachment or ask later; T25 retrieves relevant stored sections to answer.

### 3. 🔗 Website Link & Product Information Extraction
- **Option 1 (Chat Bar):** Paste any website URL (e.g. `https://amazon.com/...`, `https://wikipedia.org/...`) directly into the chat message.
- **Option 2 (Tool Button):** Click the 🔗 button on the chat bar to open the Link Ingestion dialog.
- **Automated Web Scraping:**
  - Extracts Schema.org JSON-LD and OpenGraph metadata.
  - Detects **E-Commerce Products:** Name, Price, Currency, Brand, Availability, and Ratings.
  - Detects **Articles / News:** Title, Excerpt, Author, and Full Body text.
  - Automatically indexes all sections into memory, presents a formatted product/article card, and speaks the summary aloud!

### 4. 🎙️ Two-Way Voice Interaction (STT & TTS)
- **Speech-to-Text (Microphone):** Click 🎙️ to ask questions or teach the bot by voice.
- **Text-to-Speech (Voice Output):** Reads answers aloud. Includes speed/pitch adjustments, custom voice profiles, and a 1-click mute toggle.

### 5. 🧠 Persistent Knowledge Base & 100% Offline RAG
- SQLite with **FTS5 (Full-Text Search)** and BM25 relevance scoring.
- Zero API keys needed to run out of the box!
- Optional: Connect Ollama, Google Gemini, or OpenAI in the Settings panel for generative answers.

### Using Ollama locally

1. Install and start [Ollama](https://ollama.com/download).
2. Download a model, for example: `ollama pull llama3.2`.
3. In the app's **Voice & Settings** view, select **Ollama (Local Model)**, set the model name to `llama3.2`, and save. The default Ollama URL is `http://localhost:11434`.

Chat questions are matched against the local knowledge base first; the retrieved entries are sent to Ollama as context. To search a live website, paste its URL into chat so the existing extractor can fetch and index it.

---

## 🚀 Quick Start (1-Click Run)

### Windows:
Simply double-click:
```bat
start.bat
```
*(Or in PowerShell, run `./start.ps1`)*

The server will launch at `http://127.0.0.1:8000` and automatically open in your browser.

---

## 💬 How to Use

1. **Paste a Link:** Paste a product or article URL into chat. Add a question before or after the link to get an answer from the fetched page, or paste the link alone to index it for follow-up questions.
2. **Attach a File:** Click 📎 to attach an image, PDF, Office document, or text file. Ask a question with the attachment or ask about it later.
3. **Teach a Fact:** *"Remember that the WiFi network is OfficeNet and password is Pass123"*
4. **Ask a Question:** Click 🎙️ and ask *"What is the WiFi password?"* or *"What was the price of the product I just shared?"*
