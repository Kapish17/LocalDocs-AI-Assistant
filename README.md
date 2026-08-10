# 📚 LocalDocs AI Assistant

A **NotebookLM-style RAG (Retrieval-Augmented Generation) chat application** that lets you upload your own documents, build a local knowledge base, and have a grounded conversation with your files — complete with source citations, confidence scores, OCR for scanned files, hybrid search, document summarization, and auto-generated flashcards.

🔗 **Live Demo:** [localdocs-ai-assistant.streamlit.app](https://localdocs-ai-assistant-rs35einvtpvtxc9r3yble8.streamlit.app/)
📦 **Repository:** [github.com/Kapish17/LocalDocs-AI-Assistant](https://github.com/Kapish17/LocalDocs-AI-Assistant)

---

## ✨ Features

| Feature | Description |
|---|---|
| 📤 **Multi-format Upload** | Supports PDF, DOCX, PPTX, TXT, CSV, PNG, JPG/JPEG |
| 🔍 **OCR Support** | Automatically detects and OCRs scanned PDFs / images using **EasyOCR** (pure Python, no external Tesseract binary required) |
| 🧬 **Hybrid Search** | Blends dense vector similarity (FAISS) with sparse keyword search (**BM25**) for more accurate retrieval |
| 💬 **Multi-Chat Sessions** | Create, switch between, and delete multiple independent chat threads |
| 🧠 **Conversation Memory** | Recent turns are fed back into the prompt so follow-up questions stay in context |
| 📊 **Confidence Scores & Source Citations** | Every answer shows a confidence bar and the exact source chunks (with similarity %) it was grounded on |
| 📝 **Document Summarization** | One-click AI summary of the entire knowledge base |
| 🃏 **Flashcard Generator** | Auto-generates flip-style Q&A flashcards from your documents for studying |
| 🔗 **Shareable Conversations** | Generate a read-only shareable link/export of any chat |
| ⬇️ **Export Transcripts** | Download any conversation as a Markdown file |
| 📈 **Session Analytics** | Tracks files indexed, queries asked, average confidence, and session duration |
| 🧹 **Smart Knowledge-Base Rebuild** | Automatically syncs the `data/` folder, quarantines unreadable files, and rebuilds the FAISS index cleanly on every change |

---

## 🛠️ Tech Stack

- **Frontend / App Framework:** [Streamlit](https://streamlit.io/)
- **LLM Orchestration:** [LangChain](https://www.langchain.com/) (`langchain`, `langchain-community`)
- **LLM Provider:** Google **Gemini** via `langchain-google-genai` / `google-genai`
- **Vector Store:** [FAISS](https://github.com/facebookresearch/faiss) (`faiss-cpu`)
- **Embeddings:** `sentence-transformers` / `langchain-huggingface` / `transformers` (+ `torch`)
- **Keyword Search:** `rank-bm25`
- **OCR:** `easyocr`, `opencv-python-headless`, `pymupdf` (PDF rasterization)
- **Document Parsing:** `pypdf`, `pymupdf`, `python-docx`, `python-pptx`, `docx2txt`, `pillow`, `beautifulsoup4`
- **Data Handling:** `pandas`, `numpy`
- **Config:** `python-dotenv`

---

## 📁 Project Structure

```
LocalDocs-AI-Assistant/
├── data/                # Uploaded documents live here (auto-synced with the app state)
├── llm/                 # LLM client setup (Google Gemini wrapper)
│   └── gemini.py
├── loaders/              # Document loaders / parsers for PDF, DOCX, PPTX, TXT, CSV, images
├── rag/                  # Core RAG pipeline
│   ├── index_builder.py  # Builds / rebuilds the FAISS vector store from data/
│   ├── retriever.py      # Returns a configured retriever over the vector store
│   └── prompt.py         # RAG_PROMPT template used to ground LLM answers
├── utils/                # Shared helper utilities
├── shared_chats/         # Generated JSON files for shared/read-only conversation links
├── app.py                # Alternate / core entry point
├── streamlit_app.py       # Main Streamlit application (multi-chat, OCR, hybrid search, etc.)
├── test_models.py        # Model / pipeline test script
├── requirements.txt       # Python dependencies
└── .gitignore
```

---

## ⚙️ Installation

### 1. Clone the repository

```bash
git clone https://github.com/Kapish17/LocalDocs-AI-Assistant.git
cd LocalDocs-AI-Assistant
```

### 2. Create a virtual environment (recommended)

```bash
python -m venv venv
source venv/bin/activate      # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure your Gemini API key

Create a `.env` file in the project root:

```env
GOOGLE_API_KEY=your_google_gemini_api_key_here
```

You can generate a free API key from [Google AI Studio](https://aistudio.google.com/apikey).

### 5. Run the app

```bash
streamlit run streamlit_app.py
```

The app will open automatically in your browser at `http://localhost:8501`.

---

## 🚀 Usage

1. **Upload documents** — Drag and drop PDF, DOCX, PPTX, TXT, CSV, PNG, or JPG files in the sidebar.
2. **(Optional) Enable OCR / Hybrid Search** — Toggle checkboxes in the sidebar for scanned document support and combined vector + keyword retrieval.
3. **Build the Knowledge Base** — Click **🏗️ Build Knowledge Base** to embed and index your files.
4. **Ask questions** — Use the chat box or one of the sample prompts to query your documents. Each answer includes a confidence score and expandable source citations.
5. **Summarize / Generate Flashcards** — Use the **📝 Summarize** and **🃏 Flashcards** tools in the sidebar once the knowledge base is built.
6. **Export or Share** — Download the conversation as Markdown, or generate a shareable read-only link.

---

## 🌐 Deployment

This project is deployed on **Streamlit Community Cloud**:

👉 [https://localdocs-ai-assistant-rs35einvtpvtxc9r3yble8.streamlit.app/](https://localdocs-ai-assistant-rs35einvtpvtxc9r3yble8.streamlit.app/)

To deploy your own instance:

1. Fork this repository.
2. Go to [share.streamlit.io](https://share.streamlit.io/) and connect your GitHub account.
3. Select the forked repo and set `streamlit_app.py` as the entry point.
4. Add `GOOGLE_API_KEY` under **App settings → Secrets**:
   ```toml
   GOOGLE_API_KEY = "your_google_gemini_api_key_here"
   ```
5. Deploy 🚀

---

## 🗺️ Roadmap Ideas

- [ ] Support for additional LLM providers (OpenAI, local Ollama models)
- [ ] Persistent multi-user knowledge bases
- [ ] Multi-language OCR support
- [ ] Export flashcards to Anki-compatible format

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!

1. Fork the project
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is open source. Add a `LICENSE` file (e.g., MIT) to formally declare licensing terms.

---

## 🙋 Author

**Kapish17**
GitHub: [@Kapish17](https://github.com/Kapish17)

---

⭐ If you find this project useful, consider giving it a star on [GitHub](https://github.com/Kapish17/LocalDocs-AI-Assistant)!
