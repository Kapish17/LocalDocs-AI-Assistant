# 📚 LocalDocs AI Assistant

A **NotebookLM-style RAG (Retrieval-Augmented Generation) application** that lets you upload your own documents, build a knowledge base, and have a grounded conversation with your files — complete with source citations, confidence scores, hybrid search, document summarization, and auto-generated flashcards.

🔗 **Live Demo (legacy Streamlit UI):** [localdocs-ai-assistant.streamlit.app](https://localdocs-ai-assistant-rs35einvtpvtxc9r3yble8.streamlit.app/)
📦 **Repository:** [github.com/Kapish17/LocalDocs-AI-Assistant](https://github.com/Kapish17/LocalDocs-AI-Assistant)

---

## 🏗️ Architecture

The primary application is now a **separated React frontend + FastAPI backend**, both built on top of the same RAG engine the original Streamlit app used. The Streamlit app still works and is kept as a legacy/demo interface (see [Streamlit (legacy)](#-streamlit-legacy-demo)).

```
                     USER
                      │
              React Frontend (Vite)
                      │
                 HTTP / REST
                      │
              FastAPI Backend
                      │
             Shared RAG Engine (core/, rag/, llm/)
              /                \
          FAISS               Gemini LLM
                      │
                   Docker
                      │
              Google Cloud Run (backend)
```

- **`frontend/`** — React + Vite UI. Talks to the backend only over HTTP (`VITE_API_URL`). No RAG/LLM logic here.
- **`backend/`** — FastAPI service. Thin API layer (`backend/api/`) over a framework-agnostic RAG core (`backend/core/`, `backend/rag/`, `backend/llm/`, `backend/loaders/`, `backend/utils/`) — the exact same modules the original Streamlit app used, unchanged in behavior.
- **`streamlit_app.py`** (repo root) — the original Streamlit UI, kept working, importing the same `backend/core`, `backend/rag`, `backend/llm` modules (not a second copy).

Expensive resources (the embedding model, the FAISS index, the Gemini client) are loaded once — at FastAPI startup via its `lifespan` handler, or at Streamlit session/cache time — never rebuilt per-request.

---

## ✨ Features

| Feature | Description | Where |
|---|---|---|
| 📤 **Multi-format Upload** | PDF, DOCX, PPTX, TXT, CSV, MD | React + Streamlit |
| 🔍 **OCR Support** | Per-page OCR fallback (EasyOCR + PyMuPDF) for scanned PDF pages — runs automatically during upload, no separate pass needed | React + Streamlit (shared `core/ocr.py`) |
| 🧬 **Hybrid Search with document scoping** | Blends dense vector similarity (FAISS) with sparse keyword search (BM25); optionally scoped to one document (`document_id`) so "tell me about this PDF" can never pull in another file's chunks | Shared RAG core |
| 🧭 **Broad-question detection** | Recognizes summary-style phrasing ("tell me about this pdf", "what is this document about") and samples across the whole document instead of top-k similarity, so a single keyword-matching chunk can't dominate the answer | `core/rag_engine.py` |
| 📊 **Confidence Scores & Source Citations** | Every answer shows a confidence score (retrieval-quality signal, not a correctness guarantee) and the exact chunks — with page numbers — it was grounded on | React + Streamlit |
| 📚 **Document Library** | List, search, and delete uploaded documents; per-document chunk/page counts and indexed status | React (`GET/DELETE /api/documents`) |
| 💬 **Multi-Session Chat** | Multiple isolated chat threads with their own history, auto-titling, and conversation memory fed back into the prompt | React (in-memory session store) + Streamlit |
| 📝 **Document Summarization** | Short or detailed AI summary, scoped to one document; long documents use real hierarchical (map-reduce) summarization instead of truncation | React + Streamlit, shared `summarize_documents()` |
| 🃏 **Flashcards** | Flip-card study Q&A generated from one document, with per-card source attribution | React + Streamlit, shared `generate_flashcards()` |
| 📄 **Markdown Export** | Export a chat session, a summary, or a flashcard set as a `.md` file | React (`GET .../export`) + Streamlit |

**OCR note:** OCR is applied per-page during ingestion (`loaders/pdf_loader.py` → `core/ocr.py`) — a page only gets OCR'd when its native `pypdf` text extraction is too short to be usable, so text-based pages are never unnecessarily OCR'd. This runs the same way through `POST /upload` and the Streamlit app.

---

## 🛠️ Tech Stack

- **Frontend:** [React](https://react.dev/) + [Vite](https://vitejs.dev/) (JavaScript)
- **Backend API:** [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/)
- **LLM Orchestration:** [LangChain](https://www.langchain.com/) (`langchain`, `langchain-community`)
- **LLM Provider:** Google **Gemini** via `langchain-google-genai` / `google-genai`
- **Vector Store:** [FAISS](https://github.com/facebookresearch/faiss) (`faiss-cpu`)
- **Embeddings:** `sentence-transformers` / `langchain-huggingface` / `transformers` (+ `torch`)
- **Keyword Search:** `rank-bm25`
- **OCR (Streamlit):** `easyocr`, `opencv-python-headless`, `pymupdf`
- **Document Parsing:** `pypdf`, `pymupdf`, `python-docx`, `python-pptx`, `docx2txt`, `pillow`, `beautifulsoup4`
- **Legacy UI:** [Streamlit](https://streamlit.io/)
- **Containerization / Deployment:** [Docker](https://www.docker.com/), [Docker Compose](https://docs.docker.com/compose/), [Google Cloud Run](https://cloud.google.com/run)

---

## 📁 Project Structure

```
LocalDocs-AI-Assistant/
│
├── frontend/                   # React + Vite UI (multi-page)
│   ├── src/
│   │   ├── components/
│   │   │   ├── layout/          # AppShell, Sidebar (nav + chat sessions), Topbar
│   │   │   ├── chat/            # ChatMessage (Markdown rendering), QueryBox
│   │   │   ├── upload/          # UploadPanel (drag & drop)
│   │   │   ├── sources/         # SourceList
│   │   │   └── common/          # EmptyState, ErrorBanner, ConfidenceBadge, loading states
│   │   ├── pages/               # Dashboard, Documents, Chat, Summary, Flashcards
│   │   ├── hooks/                # useDocuments, useSessions, useTheme
│   │   ├── services/             # api.js — the only file that talks to the backend
│   │   ├── utils/sessionEvents.js
│   │   ├── App.jsx               # react-router-dom routes
│   │   └── main.jsx
│   ├── public/
│   ├── package.json
│   ├── vite.config.js
│   ├── Dockerfile              # Multi-stage build -> nginx, Cloud Run-ready
│   ├── nginx.conf.template / docker-entrypoint.sh   # PORT substitution for nginx
│   ├── .env.example
│   └── README.md
│
├── backend/                    # FastAPI service
│   ├── api/
│   │   ├── main.py             # App, CORS, lifespan startup, all endpoints (see below)
│   │   └── schemas.py          # Pydantic request/response models
│   ├── core/                   # Framework-agnostic RAG logic (shared by API + Streamlit)
│   │   ├── rag_engine.py       # answer_question(), hybrid search (document-scoped), summarize, flashcards, debug tracing
│   │   ├── kb.py                # Knowledge-base bootstrap, upload/rebuild/list/delete helpers
│   │   ├── documents.py         # Document-library helpers (list with stats, resolve document_id)
│   │   ├── sessions.py          # In-memory multi-session chat store
│   │   └── ocr.py                # EasyOCR + PyMuPDF page-level OCR fallback
│   ├── rag/                    # index_builder.py, retriever.py, prompt.py, chunking.py, ...
│   ├── llm/                    # gemini.py — Gemini client setup
│   ├── loaders/                # Per-format loaders (pdf, docx, pptx, txt, csv, md) — pdf/pptx return one Document per page/slide
│   ├── utils/                  # file_scanner.py
│   ├── requirements.txt
│   ├── Dockerfile              # Cloud Run-ready backend image
│   └── .env.example
│
├── data/                       # Documents live here (shared by backend + Streamlit)
├── streamlit_app.py            # Legacy/demo Streamlit UI (kept working)
├── app.py                      # CLI entry point
├── docker-compose.yml          # Local full-stack dev: `docker compose up --build`
├── .dockerignore                # Backend image build context (repo root)
├── .env.example                 # Points to backend/.env.example + frontend/.env.example
├── .gitignore
└── README.md
```

---

## ⚙️ Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/Kapish17/LocalDocs-AI-Assistant.git
cd LocalDocs-AI-Assistant
```

### 2. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # then edit backend/.env and set GOOGLE_API_KEY
cd ..
```

Get a free Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey).

### 3. Run the backend

From the **repository root** (so `data/`/`database/` are shared with the Streamlit app):

```bash
uvicorn backend.api.main:app --reload --port 8000
```

Check it's up: `curl http://localhost:8000/health`. Interactive API docs: `http://localhost:8000/docs`.

### 4. Frontend

```bash
cd frontend
npm install
cp .env.example .env          # VITE_API_URL defaults to http://localhost:8000
npm run dev
```

Open `http://localhost:5173`. Upload a document, then ask a question.

---

## 🔌 API Endpoints (backend)

**`GET /health`** — readiness check, no request body.

```json
{ "status": "ok", "kb_ready": true, "llm_ready": true, "llm_error": null }
```

**`POST /upload`** — multipart form, one or more files under the `files` field. Saves them into `data/` and rebuilds the FAISS index (full rebuild from everything currently in `data/`, reusing the existing `build_vector_store()` pipeline — not a second implementation).

```json
{
  "files": [{ "filename": "report.pdf", "status": "indexed", "detail": null }],
  "kb_ready": true
}
```

**`POST /query`**

```json
// Request
{ "query": "What does this document say about pricing?", "document_id": "report.pdf", "session_id": null }
```

`document_id` and `session_id` are both optional. When `document_id` is set, retrieval is restricted to that document only (see [Testing Notes](#-testing-notes) for why this matters). When `session_id` is set (from `POST /api/sessions`), the question and answer are appended to that session's history and fed back into future questions in the same session.

```json
// Response
{
  "answer": "...",
  "confidence": 0.83,
  "sources": ["report.pdf"],
  "retrieved_documents": [{ "source": "report.pdf", "document_id": "report.pdf", "page": 3, "chunk_id": "report.pdf::chunk_2", "content": "...", "score": 0.83 }],
  "latency_ms": 842,
  "session_id": null
}
```

Error handling: `422` for an empty/invalid query body, `404` for an unknown `document_id`/`session_id`, `503` if no knowledge base exists yet or the Gemini client isn't configured, `502` if the LLM call itself fails — always with a human-readable `detail`, never a bare 500.

**Document library**

- `GET /api/documents` — every uploaded document with `document_id`, `file_type`, `size_bytes`, `uploaded_at`, `indexed`, `num_chunks`, `num_pages`.
- `DELETE /api/documents/{document_id}` — removes the file and rebuilds the index.

**Summarization & flashcards** (both reuse the same indexed chunks `/query` reads — no separate ingestion path)

- `POST /api/documents/{document_id}/summarize` — body `{"detail": "short" | "detailed"}` → `{document_id, summary, detail}`. Long documents are summarized hierarchically (segment summaries combined into one), not truncated.
- `POST /api/documents/{document_id}/flashcards` — body `{"num_cards": 8}` → `{document_id, flashcards: [{question, answer, source: {filename, page}}]}`.
- `GET /api/documents/{document_id}/summary/export` / `GET /api/documents/{document_id}/flashcards/export` — same content as Markdown (`text/markdown`), for direct download.

**Chat sessions** (in-memory — see the note under [Roadmap Ideas](#-roadmap-ideas))

- `POST /api/sessions` — `{"title": "optional"}` → the new session.
- `GET /api/sessions` — every session's id/title/timestamps/message count.
- `GET /api/sessions/{session_id}` — full message history for one session.
- `DELETE /api/sessions/{session_id}`.
- `GET /api/sessions/{session_id}/export` — the conversation as Markdown.

---

## 🔑 Environment Variables

| Variable | Used by | Required | Description |
|---|---|---|---|
| `GOOGLE_API_KEY` | backend | Yes | Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey) |
| `GEMINI_MODEL` | backend | No | Overrides the default Gemini model alias (`gemini-flash-lite-latest`) |
| `CORS_ORIGINS` | backend | No | Comma-separated frontend origins allowed to call the API. Defaults to `http://localhost:5173` |
| `FRONTEND_URL` | backend | No | Single-origin alternative to `CORS_ORIGINS` |
| `PORT` | backend, frontend (Docker) | No | Port the server listens on. Defaults to `8080` in Docker |
| `VITE_API_URL` | frontend | Yes (has a dev default) | Base URL of the backend. **Baked in at build time** for the frontend Docker image (Vite env vars are compile-time, not runtime) |

Never commit `backend/.env` or `frontend/.env` — only the `.env.example` files are tracked. `CORS_ORIGINS`/`FRONTEND_URL` intentionally replace `allow_origins=["*"]` so only known frontends can call the API.

---

## 🐳 Docker Compose (local full-stack)

```bash
cp backend/.env.example backend/.env   # set GOOGLE_API_KEY first
docker compose up --build
```

- Frontend → `http://localhost:5173`
- Backend → `http://localhost:8000`

`data/` and `database/` are mounted into the backend container from the repo root, so documents uploaded through the app survive a `docker compose up` restart. The frontend image is built with `VITE_API_URL=http://localhost:8000` baked in (see `docker-compose.yml`); change that build arg if the backend runs somewhere else.

> This project's sandbox test environment could not reach Docker Hub to pull base images (`python:3.12-slim`, `node:20-alpine`, `nginx:alpine`) when validating this setup, so `docker build`/`docker compose up` itself is unverified end-to-end here — see [Testing Notes](#-testing-notes) below for exactly what *was* verified and what to check when you run it. The Dockerfiles, entrypoint script, and `docker-compose.yml` follow standard, well-established patterns.

## 🐳 Docker (individual images)

**Backend** (build context is the repo root, since the image also bundles `data/`):

```bash
docker build -f backend/Dockerfile -t localdocs-backend .
docker run --rm -p 8080:8080 -e GOOGLE_API_KEY=your_key localdocs-backend
```

**Frontend:**

```bash
docker build -f frontend/Dockerfile -t localdocs-frontend \
  --build-arg VITE_API_URL=http://localhost:8080 frontend
docker run --rm -p 5173:8080 localdocs-frontend
```

Both containers listen on `0.0.0.0` and read the `PORT` env var (default `8080`), matching Cloud Run's requirements.

---

## ☁️ Google Cloud Deployment

Target production architecture:

```
React frontend (static hosting or its own container)
              │
              ▼
   FastAPI backend on Google Cloud Run
              │
              ▼
        RAG engine / Gemini
```

This uses Cloud Run's pay-per-use tier — no GPUs, no always-on infrastructure, scales to zero when idle. **These commands create real cloud resources under your own Google Cloud billing account — nothing is deployed automatically; run them yourself when ready.**

### Backend → Cloud Run

**1. Authenticate and select a project**

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

**2. Enable required services**

```bash
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
```

**3. Build the image** (Cloud Build reads `backend/Dockerfile`; run this from the repo root)

```bash
gcloud builds submit --config - --substitutions=_IMAGE=gcr.io/YOUR_PROJECT_ID/localdocs-backend <<'EOF'
steps:
  - name: gcr.io/cloud-builders/docker
    args: ['build', '-f', 'backend/Dockerfile', '-t', '$_IMAGE', '.']
images: ['$_IMAGE']
EOF
```

(Or simply: `gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/localdocs-backend backend` if you don't need `data/` baked into the image — the app then relies on documents added via `POST /upload` after each cold start.)

**4. Deploy**

```bash
gcloud run deploy localdocs-backend \
  --image gcr.io/YOUR_PROJECT_ID/localdocs-backend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_API_KEY=your_key,CORS_ORIGINS=https://your-frontend-url \
  --memory 2Gi --cpu 2
```

Prefer not to put your API key on the command line? Use Secret Manager and `--set-secrets GOOGLE_API_KEY=your-secret-name:latest` instead.

**5. Get the URL and test it**

```bash
gcloud run services describe localdocs-backend --region us-central1 --format='value(status.url)'

curl https://YOUR-BACKEND-URL/health
curl -X POST https://YOUR-BACKEND-URL/query -H "Content-Type: application/json" -d '{"query": "What is this about?"}'
```

### Frontend deployment

The React app is a static build (`npm run build` → `frontend/dist/`), so pick whichever is simpler for you:

- **Static hosting** (simplest/cheapest — e.g. Firebase Hosting, Cloud Storage + a load balancer, or any static host): build with `VITE_API_URL` set to your Cloud Run backend URL, then upload `dist/`.
  ```bash
  cd frontend
  VITE_API_URL=https://YOUR-BACKEND-URL npm run build
  # then deploy dist/ with your static host of choice
  ```
- **Cloud Run as a second service** (if you'd rather keep everything on Cloud Run): build and deploy `frontend/Dockerfile` the same way as the backend, passing `--build-arg VITE_API_URL=https://YOUR-BACKEND-URL` at build time and `--set-env-vars CORS_ORIGINS` on the *backend* redeploy to include the new frontend URL.
  ```bash
  gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/localdocs-frontend frontend
  gcloud run deploy localdocs-frontend \
    --image gcr.io/YOUR_PROJECT_ID/localdocs-frontend \
    --platform managed --region us-central1 --allow-unauthenticated
  ```

Either way, after the frontend has a URL, redeploy the backend with `--update-env-vars CORS_ORIGINS=https://your-frontend-url` so the browser's CORS preflight succeeds.

**Notes**

- The backend builds its FAISS index from whatever is in `data/` at container startup (`backend/core/kb.py`). Cloud Run instances are stateless, so a knowledge base built from an uploaded file does not persist across a fresh instance unless the documents are also baked into the image or re-uploaded after a cold start.
- To tear down and stop being billed: `gcloud run services delete localdocs-backend --region us-central1` (and `localdocs-frontend` if deployed).

---

## 🐍 Streamlit (legacy demo)

The original Streamlit UI still works, unchanged in behavior, importing the same backend RAG modules (not a duplicate implementation):

```bash
pip install -r backend/requirements.txt   # if not already installed
streamlit run streamlit_app.py
```

Run from the repository root so it shares `data/`/`database/` with the FastAPI backend. It's deployed on Streamlit Community Cloud:

👉 [https://localdocs-ai-assistant-rs35einvtpvtxc9r3yble8.streamlit.app/](https://localdocs-ai-assistant-rs35einvtpvtxc9r3yble8.streamlit.app/)

To deploy your own instance: fork the repo, connect it at [share.streamlit.io](https://share.streamlit.io/), set `streamlit_app.py` as the entry point, and add `GOOGLE_API_KEY` under **App settings → Secrets**.

---

## 🐛 The "tell me about this PDF" bug — root cause and fix

Uploading a PDF and asking "tell me about this pdf" used to return an explanation of *how the software technically handles PDFs* (pypdf extraction, OCR fallback, etc.) instead of the document's actual content — even though the sources panel showed real chunks from the file.

**Root cause (proven with a real reproduction, not guessed):** two compounding bugs in retrieval, not in the LLM prompt or the frontend.

1. `is_broad_question()` didn't recognize "tell me about this pdf" as a summary-style question, so it fell through to ordinary top-k hybrid search instead of whole-document sampling.
2. Inside hybrid search, BM25 (45% of the blended score) does literal keyword matching — and a chunk describing *this project's own* "PDFs are handled using pypdf extraction..." happened to repeat the word "pdf" more than the chunks that were actually about the document's subject, so it won the literal-keyword race and got sent to Gemini as the top context.
3. A structural gap made it worse: there was no per-document filtering anywhere in retrieval, so with multiple documents uploaded this class of bug would also cause cross-document contamination, not just a wrong chunk within one document.

This was reproduced with the real, unmodified retrieval code (`hybrid_search`, `is_broad_question`, real `rank_bm25.BM25Okapi`) against hand-authored chunks mirroring the real document's structure — only the embedding model and Gemini were faked, since this sandbox has no network access to huggingface.co or the Gemini API. The reproduction printed the exact top-ranked chunk and confirmed it was the self-referential "how PDFs are handled" decoy.

**Fix:**
- `is_broad_question()` now also matches a regex pattern covering phrasings like "tell me about this pdf" / "what is this document about" / "explain this file", so these questions route to whole-document sampling instead of keyword search.
- Retrieval (`get_all_docs`, `vector_search`, `_build_bm25`, `hybrid_search`, `get_context_and_scores`) now accepts a `document_filter` end-to-end, so a document-specific question can be — and by default in the frontend, is — scoped to just that document's own chunks. BM25 gets a genuinely separate per-document index, not a global index post-filtered.
- `RAG_PROMPT` was hardened with an explicit instruction not to confuse a document's own subject matter (which may itself be *about* RAG/software concepts) with a description of the assistant's own implementation.

Verified fixed: re-running the same reproduction after the fix shows `is_broad_question("tell me about this pdf")` now returns `True`, and the top-ranked/sampled chunk is the document's real overview — not the decoy. This was then re-verified a second time through the real FastAPI endpoint and, a third time, through the actual React UI driven by a headless browser (see below) — same result at every layer.

---

## 🧪 Testing Notes

What was actually run and verified while building this (not just "should work"):

- **Backend, unit level:** `py_compile` on every modified module. The PDF-answer bug above was reproduced and re-verified with real (unmodified) retrieval logic and only faked embeddings/LLM.
- **Backend, API level:** a live FastAPI app (real `TestClient`, real routes, real `core.rag_engine`, real FAISS + BM25, only embeddings/Gemini faked) was driven through: health check; document listing with correct per-page/per-chunk counts from real PDF/DOCX/TXT files; a document-scoped query reproducing the exact bug scenario (confirmed fixed, and confirmed sources never include another uploaded document); an invalid `document_id` returning 404; summarize (short); flashcards with per-card source attribution; both Markdown export endpoints; creating two chat sessions and confirming their histories stay isolated from each other; deleting a session and a document and confirming both 404 afterward and the document disappears from the library.
- **Frontend, build level:** `npm install` and `npm run build` both succeed with no errors.
- **Frontend, full end-to-end:** a live Vite dev server was driven with a real headless browser (Playwright/Chromium) against the live backend above, exercising the real UI: Dashboard loads real stats; Documents page lists real uploaded files; asking "tell me about this pdf" scoped to one document renders a real, non-implementation-leaking answer with a confidence badge and an expandable, matching sources panel; a chat session is auto-created and immediately visible in the sidebar (a stale-sidebar bug found and fixed during this testing — see below); Summary page generates and renders Markdown, and the short/detailed toggle regenerates; Flashcards page generates cards, flips, and navigates; theme toggle switches and persists the `data-theme` attribute; mobile viewport (390×844) renders correctly. Console/page errors were captured on every run — the final run captured zero.
- **Two real bugs were found and fixed by this end-to-end testing** (not just by writing the code): (1) the chat sidebar's session list didn't refresh when a session was created from the Chat page itself (each `useSessions()` call held independent state) — fixed with a small event bus so any session mutation notifies every instance; (2) on mobile, the sidebar becomes `position: fixed` to slide in/out, which removes it from the CSS grid's item flow entirely — without an explicit `grid-column: 2` on the main content area, it collapsed into the sidebar's 0px track instead of the content track, squeezing the entire app into a ~40px-wide sliver on phones. Both were caught by rendering real screenshots and inspecting real computed layout, not by inspection alone.
- **Docker:** the Dockerfiles, `docker-compose.yml`, and the nginx `PORT` templating (`envsubst '${PORT}' < nginx.conf.template`) were reviewed and the substitution logic verified directly; `docker build` itself could not be completed in the sandbox this was built in, because that sandbox's network policy blocks Docker Hub entirely (`python:3.12-slim`, `node:20-alpine`, `nginx:alpine` all failed to pull with `403 Forbidden`). Everything each image depends on — dependency installation, the exact startup commands, and the app logic — was verified outside Docker as described above. Run `docker compose up --build` once yourself to confirm the image layers build cleanly; if anything surfaces there, it will be Docker-layer only (base image versions, apt package names), not the application code.
- The embedding model (`BAAI/bge-small-en-v1.5`, downloaded from Hugging Face on first run) and the Gemini API also couldn't be reached in that same sandbox for the same network-policy reason — all tests above used a fake in-memory embeddings implementation and a fake deterministic LLM to exercise the exact same code paths (real chunking, real FAISS, real BM25, real prompt construction, real API routing, real React rendering) without needing that network access. This already works on a real machine with normal internet access (confirmed by the existing, working FAISS index this project ships with).

Real-money cloud resources were never created — the Cloud Run commands above are yours to run.

**What was not tested end-to-end in this sandbox:** OCR on an actual scanned PDF — the OCR code path (`core/ocr.py`: EasyOCR + PyMuPDF, gated on `needs_ocr()`) was reviewed but not exercised, since EasyOCR downloads its own model from the network on first use and that's blocked in this sandbox the same way Hugging Face and the Gemini API are; real Gemini responses (all LLM calls were faked, as noted above); Docker image builds (network-blocked, as noted above).

---

## 🗺️ Roadmap Ideas / Known Limitations

- **Chat sessions are in-memory** — `core/sessions.py` is a process-wide dict, not a database. Sessions reset on backend restart. This is a deliberate, scoped decision for a project this size (there's no database anywhere else in the project either), not an oversight — adding persistence (SQLite would be the natural next step) is the main thing standing between this and a "real" multi-user deployment.
- **Flashcard source attribution is best-effort** — a card is attributed to a page only when every retrieved chunk for that document came from a single page; a card drawing on content spanning multiple pages is attributed to the document as a whole rather than guessing a page.
- **Page counts can undercount** — a PDF page with no extractable text and no successful OCR produces an empty chunk that the text splitter drops, so `num_pages` in the document library reflects pages that produced at least one chunk, not the PDF's total page count in every case.
- [ ] Persist chat sessions (SQLite) instead of in-memory
- [ ] Support for additional LLM providers (OpenAI, local Ollama models)
- [ ] Persistent multi-user knowledge bases (currently single-tenant, matching the original app's scope)
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
