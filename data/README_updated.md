<div align="center">

<!-- Animated Typing Header -->
<a href="https://github.com/Kapish17/VisionGuard-AI">
  <img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=700&size=32&pause=1000&color=00D9FF&center=true&vCenter=true&width=700&lines=VisionGuard+AI+%F0%9F%9B%A1%EF%B8%8F;AI-Powered+Investigation+Platform;Computer+Vision+%2B+RAG+%2B+LLMs;Search+Video.+Search+Docs.+Search+Truth." alt="Typing SVG" />
</a>

<h3>🔍 An Intelligent AI Investigation Platform using Computer Vision, Retrieval-Augmented Generation (RAG), and Large Language Models</h3>

<br/>

<!-- Badges -->
<p>
  <img src="https://img.shields.io/github/stars/arshraj1020/VisionGuard-AI?style=for-the-badge&color=00D9FF&labelColor=0d1117" alt="Stars"/>
  <img src="https://img.shields.io/github/forks/arshraj1020/VisionGuard-AI?style=for-the-badge&color=00D9FF&labelColor=0d1117" alt="Forks"/>
  <img src="https://img.shields.io/github/issues/arshraj1020/VisionGuard-AI?style=for-the-badge&color=00D9FF&labelColor=0d1117" alt="Issues"/>
  <img src="https://img.shields.io/github/last-commit/arshraj1020/VisionGuard-AI?style=for-the-badge&color=00D9FF&labelColor=0d1117" alt="Last Commit"/>
</p>
<p>
  <img src="https://img.shields.io/badge/License-MIT-00D9FF?style=for-the-badge&labelColor=0d1117" alt="License"/>
  <img src="https://img.shields.io/badge/Build-Passing-success?style=for-the-badge&labelColor=0d1117" alt="Build"/>
  <img src="https://img.shields.io/badge/PRs-Welcome-00D9FF?style=for-the-badge&labelColor=0d1117" alt="PRs Welcome"/>
  <img src="https://img.shields.io/badge/Made%20with-%E2%9D%A4%EF%B8%8F-red?style=for-the-badge&labelColor=0d1117" alt="Made with love"/>
</p>

<!-- Visitor counter -->
<img src="https://komarev.com/ghpvc/?username=VisionGuard-AI&label=Repository%20Views&color=00D9FF&style=for-the-badge" alt="Visitor Count"/>

<br/><br/>

<!-- Hero Banner (SVG style) -->
<img src="https://capsule-render.vercel.app/api?type=waving&color=0:0d1117,100:00D9FF&height=200&section=header&text=VisionGuard%20AI&fontSize=60&fontColor=ffffff&animation=fadeIn&fontAlignY=38&desc=Turning%20Surveillance%20Footage%20Into%20Searchable%20Evidence&descAlignY=58&descSize=18" width="100%"/>

<br/>

<a href="#-quick-start">🚀 Quick Start</a> •
<a href="#-features">✨ Features</a> •
<a href="#-architecture">🏗️ Architecture</a> •
<a href="#-demo">🎬 Demo</a> •
<a href="#-roadmap">🗺️ Roadmap</a>

</div>

<br/>

---

## 📚 Table of Contents

<details open>
<summary><b>Click to expand / collapse</b></summary>

- [📖 About The Project](#-about-the-project)
- [✨ Features](#-features)
- [🏗️ Architecture](#-architecture)
- [🔄 Workflow Pipeline](#-workflow-pipeline)
- [🧠 AI Investigation Pipeline](#-ai-investigation-pipeline)
- [🛠️ Tech Stack](#-tech-stack)
- [📁 Folder Structure](#-folder-structure)
- [🚀 Quick Start](#-quick-start)
- [⚙️ Environment Variables](#-environment-variables)
- [📡 API Overview](#-api-overview)
- [🎬 Demo](#-demo)
- [🖼️ Screenshots](#-screenshots)
- [🗺️ Roadmap](#-roadmap)
- [🔮 Future Scope](#-future-scope)
- [📜 License](#-license)
- [🙏 Acknowledgements](#-acknowledgements)
- [📬 Contact](#-contact)

</details>

---

## 📖 About The Project

> **VisionGuard AI** is an AI-powered investigation assistant that transforms CCTV footage and investigation documents into **searchable evidence**.

Instead of manually watching hours of surveillance footage, investigators simply upload:

🎥 CCTV videos &nbsp;•&nbsp; 📄 Incident reports &nbsp;•&nbsp; 🗣️ Witness statements &nbsp;•&nbsp; 🔐 Security logs

VisionGuard AI uses **Computer Vision** to detect events, **RAG** to retrieve relevant evidence, and an **LLM** to answer natural language investigation queries — turning tedious manual review into instant, conversational insight.

### 💬 Example Queries

```
🔎 "Who entered Gate B after 9 PM?"
🔎 "Show everyone carrying a backpack."
🔎 "Track the suspect across cameras."
🔎 "Generate today's investigation report."
```

<div align="center">

**No more scrubbing through hours of footage. Just ask.**

</div>

---

## ✨ Features

<div align="center">

| 🎥 Video Intelligence | 📄 Document Intelligence | 🧠 AI Investigation | 🔗 RAG Engine |
|:---:|:---:|:---:|:---:|
| Video Upload | PDF Upload | Natural Language Search | LangChain |
| YOLO Object Detection | OCR | Timeline Generation | ChromaDB |
| ByteTrack Multi-Object Tracking | Incident Report Parsing | Automated Report Generation | Context-Aware Retrieval |
| Event Timeline Generation | Witness Statement Parsing | Evidence Explanation | Semantic Chunking |

</div>

<details>
<summary><b>🎥 Video Intelligence — Click to expand</b></summary>
<br/>

- **Video Upload** — Drag-and-drop CCTV footage ingestion pipeline
- **YOLO Object Detection** — Real-time detection of people, objects & anomalies
- **ByteTrack Tracking** — Persistent multi-object tracking across frames
- **Event Timeline Generation** — Auto-generated, timestamped event logs

</details>

<details>
<summary><b>📄 Document Intelligence — Click to expand</b></summary>
<br/>

- **PDF Upload** — Bulk ingestion of case-related documents
- **OCR** — Extracts text from scanned reports and images
- **Incident Reports** — Structured parsing of official reports
- **Witness Statements** — NLP-based statement analysis

</details>

<details>
<summary><b>🧠 AI Investigation — Click to expand</b></summary>
<br/>

- **Natural Language Search** — Ask questions like you're talking to a detective partner
- **Timeline Generation** — Cross-references video + document evidence
- **Report Generation** — One-click investigation summaries
- **Evidence Explanation** — LLM explains *why* a result matches your query

</details>

---

## 🏗️ Architecture

```mermaid
flowchart TD
    A["🖥️ Frontend<br/>React + Tailwind CSS"] -->|REST API| B["⚙️ Backend<br/>FastAPI"]
    B --> C["👁️ Computer Vision<br/>YOLO + ByteTrack"]
    B --> D["🗄️ Database<br/>PostgreSQL"]
    B --> E["🔗 Vector Database<br/>ChromaDB"]
    E --> F["🧠 LLM Engine<br/>GPT / Llama"]
    C --> D
    D --> E
    F -->|Response| B
    B -->|JSON| A

    style A fill:#0d1117,stroke:#00D9FF,stroke-width:2px,color:#fff
    style B fill:#0d1117,stroke:#00D9FF,stroke-width:2px,color:#fff
    style C fill:#0d1117,stroke:#00D9FF,stroke-width:2px,color:#fff
    style D fill:#0d1117,stroke:#00D9FF,stroke-width:2px,color:#fff
    style E fill:#0d1117,stroke:#00D9FF,stroke-width:2px,color:#fff
    style F fill:#0d1117,stroke:#00D9FF,stroke-width:2px,color:#fff
```

---

## 🔄 Workflow Pipeline

```mermaid
sequenceDiagram
    actor Investigator
    participant UI as React Dashboard
    participant API as FastAPI Backend
    participant CV as YOLO + ByteTrack
    participant DB as PostgreSQL
    participant Vec as ChromaDB
    participant LLM as LLM Engine

    Investigator->>UI: Upload CCTV video / documents
    UI->>API: POST /upload
    API->>CV: Process video frames
    CV->>DB: Store detected events & timestamps
    API->>Vec: Embed & index evidence
    Investigator->>UI: Ask natural language query
    UI->>API: POST /query
    API->>Vec: Retrieve relevant context (RAG)
    Vec->>LLM: Pass retrieved evidence
    LLM->>API: Generate grounded answer
    API->>UI: Return response
    UI->>Investigator: Display answer + evidence
```

---

## 🧠 AI Investigation Pipeline

```mermaid
graph LR
    A["📥 Raw Input<br/>Video / Docs"] --> B["🔍 Detection<br/>YOLO + OCR"]
    B --> C["🧩 Feature Extraction"]
    C --> D["🗂️ Embedding<br/>ChromaDB"]
    D --> E["🔎 Retrieval<br/>RAG"]
    E --> F["🤖 LLM Reasoning"]
    F --> G["📊 Investigation Report"]

    style A fill:#0d1117,stroke:#00D9FF,color:#fff
    style B fill:#0d1117,stroke:#00D9FF,color:#fff
    style C fill:#0d1117,stroke:#00D9FF,color:#fff
    style D fill:#0d1117,stroke:#00D9FF,color:#fff
    style E fill:#0d1117,stroke:#00D9FF,color:#fff
    style F fill:#0d1117,stroke:#00D9FF,color:#fff
    style G fill:#0d1117,stroke:#00D9FF,color:#fff
```

---

## 🛠️ Tech Stack

<div align="center">

### Frontend
![React](https://skillicons.dev/icons?i=react,tailwind)

### Backend
![Backend](https://skillicons.dev/icons?i=fastapi,python)

### AI / Computer Vision
![AI](https://skillicons.dev/icons?i=pytorch,opencv)

### Database & Vector Store
![DB](https://skillicons.dev/icons?i=postgres)

### Deployment
![Deploy](https://skillicons.dev/icons?i=docker,github)

</div>

<div align="center">

| Layer | Technology |
|---|---|
| **Frontend** | React, Tailwind CSS |
| **Backend** | FastAPI, Python |
| **Computer Vision** | YOLO, ByteTrack |
| **RAG** | LangChain, ChromaDB |
| **LLM** | GPT (current), Llama (planned) |
| **Database** | PostgreSQL |
| **Deployment** | Docker |

</div>

---

## 📁 Folder Structure

```
VisionGuard-AI/
├── 🖥️ frontend/          # React + Tailwind UI
├── ⚙️ backend/           # FastAPI application layer
├── 👁️ ai/                # YOLO, ByteTrack, CV models
├── 🔗 rag/               # LangChain + ChromaDB retrieval logic
├── 🗄️ database/          # PostgreSQL schemas & migrations
├── 📄 docs/              # Documentation
└── 🎨 assets/            # Images, diagrams, banners
```

---

## 🚀 Quick Start

### ✅ Prerequisites

- Python 3.10+
- Node.js 18+
- Docker & Docker Compose
- PostgreSQL 14+

### 📦 Installation

```bash
# 1. Clone the repository
git clone https://github.com/Kapish17/VisionGuard-AI.git
cd VisionGuard-AI

# 2. Set up the backend
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Set up the frontend
cd ../frontend
npm install

# 4. Configure environment variables
cp .env.example .env
```

### ▶️ Running Locally

<details>
<summary><b>Option A — Run with Docker (Recommended)</b></summary>

```bash
docker-compose up --build
```

</details>

<details>
<summary><b>Option B — Run Manually</b></summary>

```bash
# Terminal 1 — Backend
cd backend
uvicorn main:app --reload

# Terminal 2 — Frontend
cd frontend
npm run dev
```

</details>

App will be live at `http://localhost:3000` 🎉

---

## ⚙️ Environment Variables

Create a `.env` file in the `backend/` directory:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/visionguard

# Vector Store
CHROMA_DB_PATH=./chroma_data

# LLM
OPENAI_API_KEY=your_openai_api_key_here

# App Config
SECRET_KEY=your_secret_key_here
ENVIRONMENT=development
```

---

## 📡 API Overview

<div align="center">

| Method | Endpoint | Description |
|:---:|---|---|
| `POST` | `/api/upload/video` | Upload CCTV footage for processing |
| `POST` | `/api/upload/document` | Upload incident reports / statements |
| `POST` | `/api/query` | Ask a natural language investigation query |
| `GET` | `/api/timeline/{case_id}` | Retrieve generated event timeline |
| `GET` | `/api/report/{case_id}` | Generate/download investigation report |
| `GET` | `/api/health` | Health check endpoint |

</div>

> 📘 Full interactive API docs available at `/docs` (Swagger UI) once the backend is running.

---

## 🎬 Demo

<div align="center">

![Demo GIF Placeholder](https://via.placeholder.com/800x400/0d1117/00D9FF?text=%F0%9F%8E%AC+Demo+GIF+Coming+Soon)

*A full walkthrough demo will be added here.*

</div>

---

## 🖼️ Screenshots

<div align="center">

| Dashboard | Investigation Chat |
|:---:|:---:|
| ![Dashboard](https://via.placeholder.com/400x250/0d1117/00D9FF?text=Dashboard) | ![Chat](https://via.placeholder.com/400x250/0d1117/00D9FF?text=AI+Chat) |

| Timeline View | Evidence Panel |
|:---:|:---:|
| ![Timeline](https://via.placeholder.com/400x250/0d1117/00D9FF?text=Timeline) | ![Evidence](https://via.placeholder.com/400x250/0d1117/00D9FF?text=Evidence+Panel) |

</div>

---

## 🗺️ Roadmap

<div align="center">

### 🔴 Phase 1 — Foundation
`Progress: ░░░░░░░░░░ 0%`

</div>

- [ ] Authentication
- [ ] Video Upload
- [ ] Document Upload
- [ ] YOLO Integration
- [ ] AI Chat
- [ ] Dashboard

<div align="center">

### 🔴 Phase 2 — Intelligence Layer
`Progress: ░░░░░░░░░░ 0%`

</div>

- [ ] Timeline Generation
- [ ] Report Generation
- [ ] Advanced Search
- [ ] Analytics Dashboard

<div align="center">

### 🔴 Phase 3 — Scale & Advanced CV
`Progress: ░░░░░░░░░░ 0%`

</div>

- [ ] Multi-camera Tracking
- [ ] Face Recognition *(optional, privacy-compliant)*
- [ ] Cloud Deployment

---

## 🔮 Future Scope

- 🌐 Multi-language support for global investigation teams
- 📱 Mobile companion app for field investigators
- 🛰️ Real-time live CCTV stream analysis
- 🔒 End-to-end encrypted evidence chain-of-custody
- 🧬 Fine-tuned domain-specific LLM for forensic reasoning
- ☁️ Full cloud-native, horizontally scalable deployment

---

## 📜 License

Distributed under the **MIT License**. See `LICENSE` for more information.

<img src="https://img.shields.io/badge/License-MIT-00D9FF?style=for-the-badge&labelColor=0d1117" alt="MIT License"/>

---

## 🙏 Acknowledgements

- [Ultralytics YOLO](https://github.com/ultralytics/ultralytics) for real-time object detection
- [LangChain](https://www.langchain.com/) for RAG orchestration
- [ChromaDB](https://www.trychroma.com/) for vector storage
- [FastAPI](https://fastapi.tiangolo.com/) for the backend framework
- [Skillicons](https://skillicons.dev/) & [Shields.io](https://shields.io/) for badges and icons
- The open-source community ❤️

---

## 📬 Contact

<div align="center">

**Kapish Kela** — Full Stack & AI Developer

[![GitHub](https://img.shields.io/badge/GitHub-Kapish17-0d1117?style=for-the-badge&logo=github&logoColor=00D9FF)](https://github.com/Kapish17)

Project Link: [https://github.com/Kapish17/VisionGuard-AI](https://github.com/Kapish17/VisionGuard-AI)

<br/>

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:00D9FF,100:0d1117&height=120&section=footer" width="100%"/>

### ⭐ If you find this project useful, consider giving it a star!

</div>
