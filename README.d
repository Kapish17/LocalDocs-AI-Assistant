# 📚 LocalDocs AI Assistant

<div align="center">

**A NotebookLM-inspired AI assistant to chat with your own documents — powered by RAG, Google Gemini, Hybrid Search, and OCR.**

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-App-FF4B4B?logo=streamlit&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-RAG-1C3C3C?logo=langchain&logoColor=white)
![Gemini](https://img.shields.io/badge/Google-Gemini-8E75B2?logo=google&logoColor=white)
![FAISS](https://img.shields.io/badge/FAISS-VectorDB-005571)
![License](https://img.shields.io/badge/License-MIT-yellow)
![Stars](https://img.shields.io/github/stars/Kapish17/LocalDocs-AI-Assistant?style=social)

[Overview](#-overview) • [Features](#-features) • [Architecture](#️-architecture) • [Installation](#-installation) • [Usage](#-usage) • [Roadmap](#-roadmap)

</div>

---

## 📖 Overview

**LocalDocs AI Assistant** lets you upload your own documents and have natural, grounded conversations with them — instead of manually scrolling through long PDFs or notes.

It uses **Retrieval-Augmented Generation (RAG)** to fetch the most relevant chunks of your documents and passes them to **Google Gemini** to generate accurate, source-backed answers.

Inspired by **Google NotebookLM**, it goes further by combining semantic + keyword hybrid search, OCR for scanned files, AI-generated flashcards, multi-chat sessions, and shareable conversations — all wrapped in a clean **Streamlit** interface.

---

## ✨ Features

### 🤖 AI-Powered Question Answering
- Natural language Q&A over your documents
- Context-aware, grounded responses via RAG
- Powered by Google Gemini LLM
- Full conversation history retained per chat

### 📄 Multi-Document Support
Upload and query across multiple formats at once:

| Format | Format | Format |
|--------|--------|--------|
| PDF | DOCX | PPTX |
| TXT | CSV | PNG |
| JPG | JPEG | — |

### 🔍 Hybrid Search
Combines **Semantic Search (FAISS)** with **Keyword Search (BM25)** for significantly better retrieval accuracy — especially on technical or jargon-heavy documents.

### 🧠 Retrieval-Augmented Generation (RAG)
```
Upload → Extract → Chunk → Embed → Store (FAISS)
       → Retrieve → Augment Prompt → Gemini → Grounded Answer
```

### 📚 OCR Support
Automatically detects scanned/image-based PDFs and runs OCR before indexing.
- Tesseract OCR engine
- Image OCR (PNG/JPG)
- PDF OCR via PyMuPDF
- Fully automatic — no manual toggling needed

### 📝 AI Document Summarization
One-click summaries covering key points, important concepts, facts, and conclusions.

### 🃏 AI Flashcards
Auto-generated Q&A flashcards with interactive flip animations — built for exam prep and quick revision.

### 💬 Multi-Chat System
- Create unlimited independent chats
- Switch between conversations instantly
- Delete chats you no longer need
- Each chat keeps its own isolated memory

### 🧠 Conversation Memory
Remembers prior turns in a chat so follow-up questions are answered with full context.

### 📈 Confidence Score
Every response ships with a confidence indicator derived from retrieval similarity.

### 📄 Source Attribution
Answers are traceable — each response shows the source document, similarity score, and retrieved references, with duplicates automatically filtered out.

### 🔗 Conversation Sharing
Generate read-only shareable links for any conversation, backed by JSON storage.

### 📥 Conversation Export
Export any chat as a clean Markdown file for notes, documentation, or revision.

### 📊 Session Analytics
Track uploaded files, total queries, average confidence, and session duration at a glance.

---

## 🏗️ Architecture

```
                     Upload Documents
                            │
                            ▼
                     Document Loader
                            │
                            ▼
                     Text Extraction
                            │
              ┌─────────────┴─────────────┐
              │                           │
              ▼                           ▼
        Native Text                 OCR Pipeline
              │                           │
              └─────────────┬─────────────┘
                            ▼
                     Document Chunking
                            ▼
                   Embedding Generation
                            ▼
                     FAISS Vector DB
                            ▼
             Hybrid Retrieval (FAISS + BM25)
                            ▼
                    Google Gemini LLM
                            ▼
                  AI Generated Response
```

---

## 🗂️ Project Structure

```
LocalDocs-AI-Assistant/
│
├── data/                     # Uploaded / sample documents
├── database/
│   └── faiss_index/           # Persisted FAISS vector store
│
├── loaders/
│   ├── pdf_loader.py           # PDF text + OCR extraction
│   ├── docx_loader.py          # DOCX parsing
│   ├── ppt_loader.py           # PPTX parsing
│   └── loader_manager.py       # Format routing
│
├── rag/
│   ├── chunking.py             # Document chunking strategy
│   ├── embeddings.py           # Embedding generation
│   ├── retriever.py            # Hybrid (FAISS + BM25) retrieval
│   ├── vector_store.py         # FAISS index management
│   ├── prompt.py                # Prompt templates
│   └── index_builder.py        # Index construction pipeline
│
├── llm/
│   └── gemini.py               # Google Gemini integration
│
├── utils/
│   └── file_scanner.py         # File type detection / scanning
│
├── shared_chats/               # JSON storage for shared conversations
│
├── app.py                      # Application entry point
├── streamlit_app.py            # Streamlit UI
├── requirements.txt
└── README.md
```

---

## ⚙️ Tech Stack

| Category | Technologies |
|---|---|
| **Language** | Python |
| **AI / LLM** | Google Gemini, LangChain |
| **Vector DB** | FAISS |
| **Search** | BM25, Hybrid Search |
| **Frontend** | Streamlit, HTML, CSS |
| **OCR** | Tesseract OCR, PyMuPDF, Pillow |
| **Core Libraries** | LangChain, FAISS, PyPDF, Pandas, NumPy, pytesseract, rank_bm25 |

---

## 🚀 Installation

**1. Clone the repository**
```bash
git clone https://github.com/Kapish17/LocalDocs-AI-Assistant.git
cd LocalDocs-AI-Assistant
```

**2. Create a virtual environment (recommended)**
```bash
python -m venv venv
source venv/bin/activate      # On Windows: venv\Scripts\activate
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Configure environment variables**

Create a `.env` file in the project root:
```env
GOOGLE_API_KEY=your_google_gemini_api_key
```

**5. Run the application**
```bash
streamlit run streamlit_app.py
```

The app will be available at `http://localhost:8501` 🎉

---

## 🧑‍💻 Usage

1. **Upload** one or more documents (PDF, DOCX, PPTX, TXT, CSV, or images)
2. Wait for the pipeline to **extract, chunk, and index** your content
3. **Ask questions** in the chat — get grounded answers with source citations and confidence scores
4. Generate a **summary** or **flashcards** for quick review
5. **Export** or **share** the conversation when you're done

---

## 🔮 Roadmap

- [ ] Voice Chat
- [ ] PDF Annotation
- [ ] Multi-user Authentication
- [ ] Cloud Storage Integration
- [ ] Image Understanding
- [ ] Table Extraction
- [ ] Citation Export
- [ ] AI Notes Generation
- [ ] Dark / Light Theme
- [ ] Agentic RAG
- [ ] Web Search Integration

---

## 🎯 Use Cases

- 🎓 Students revising for exams
- 🔬 Researchers digesting papers
- 🏫 Professors organizing course material
- 📄 Technical documentation Q&A
- ⚖️ Legal document review
- 🩺 Medical report analysis
- 🏢 Company knowledge bases
- 💼 Interview preparation

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!

1. Fork the project
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📜 License

This project is licensed under the **MIT License**.

---

## 👨‍💻 Author

**Kapish Girish Kela**
B.Tech CSE (AI & ML) — VIT Bhopal University

[![GitHub](https://img.shields.io/badge/GitHub-Kapish17-181717?logo=github)](https://github.com/Kapish17)

---

<div align="center">

### ⭐ If you found this project useful, consider giving it a star!

</div>

