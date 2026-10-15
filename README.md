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

### 2b. 🔎 Automatic Analysis & Web Research
After a PDF or document is stored, T25 keeps working in the background:
1. **Analyses** it with your AI model: title, document type, summary, key points and topics.
2. **Researches** the main topics on the web (DuckDuckGo, no API key) and saves the most useful pages.
3. **Writes a research brief** comparing the document with what the web says, with numbered sources.

The full report is posted in the chat when ready and everything is saved to the Knowledge Base (categories *PDF Document* and *Research*), so you can ask about the document, its analysis, or the research in any future session. Uploading a file with the same name again replaces the earlier copy. On a CPU-only machine with `llama3.1:8b` a run takes a few minutes; a smaller model such as `llama3.2` (3B) is faster.

### 3. 🔗 Website Link & Product Information Extraction
- **Option 1 (Chat Bar):** Paste any website URL (e.g. `https://amazon.com/...`, `https://wikipedia.org/...`) directly into the chat message. When asked a question with the link, T25 fetches up to 4,000 characters of cleaned page text and includes it with your question in the configured AI provider's context.
- **Option 2 (Tool Button):** Click the 🔗 button on the chat bar to open the Link Ingestion dialog.
- **Automated Web Scraping:**
  - Extracts Schema.org JSON-LD and OpenGraph metadata.
  - Detects **E-Commerce Products:** Name, Price, Currency, Brand, Availability, and Ratings.
  - Detects **Articles / News:** Title, Excerpt, Author, and Full Body text.
  - Automatically indexes all sections into memory, presents a formatted product/article card, and speaks the summary aloud!
- **Automatic Yahoo Search:** For questions without a supplied URL, T25 searches Yahoo, reads up to three result pages, and saves retrieved sections and generated answers for later recall.

### 4. 🎙️ Two-Way Voice Interaction (STT & TTS)
- **Speech-to-Text (Microphone):** Click 🎙️ to ask questions or teach the bot by voice.
- **Text-to-Speech (Voice Output):** Reads answers aloud. Includes speed/pitch adjustments, custom voice profiles, and a 1-click mute toggle.

### 5. 🧠 Persistent Knowledge Base & Offline Fallback
- SQLite with **FTS5 (Full-Text Search)** and BM25 relevance scoring.
- Local answers need no API key. Yahoo lookups require an internet connection; Gemini/OpenAI answers require their respective API keys.
- Optional: Connect Ollama, Google Gemini, or OpenAI in the Settings panel for generative answers.

### Using Ollama locally

1. Install and start [Ollama](https://ollama.com/download).
2. Download a chat model and the PDF embedding model: `ollama pull llama3.2` and `ollama pull nomic-embed-text`.
3. Ollama with `llama3.2` is the default provider. To change it, open the **Voice & Settings** view, pick a provider/model and save. The default Ollama URL is `http://localhost:11434`.

### PDF vector search

Install PDF/vector dependencies with `pip install chromadb langchain-text-splitters pypdf requests`, then install the Ollama embedding model with `ollama pull nomic-embed-text`. PDFs uploaded through the normal upload flow or `/upload-pdf` are chunked and indexed in the local `./chroma_db` directory. The chat searches PDF chunks first; Yahoo search is used when there is no relevant PDF context or the question asks for current web information. Retrieved PDF and web context is sent to the selected Ollama chat model.

Chat questions are also matched against the local knowledge base; retrieved pages and saved entries are sent to the selected answer provider as context. To fetch a specific live website, paste its URL into chat so the existing extractor can fetch and index it.

### Using Gemini with Yahoo web search

1. Open **Voice & Settings** and choose **Google Gemini API** as the Intelligence Provider.
2. Enter your Gemini API key and model, then save settings.
3. Ask a question normally. T25 searches Yahoo, retrieves readable result pages, and sends the question and sources to Gemini. The answer and source links are saved in the Knowledge Base for later recall.

Yahoo search requires an internet connection. Without a configured Gemini key, answers use the selected provider; fetched Yahoo sources are still saved and searchable.
Questions are sent to Yahoo for search. When Gemini is selected, the question and retrieved source text are also sent to Google's Gemini API. Search results and answers are stored in the local Knowledge Base.

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
