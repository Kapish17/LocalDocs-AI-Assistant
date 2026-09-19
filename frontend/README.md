# LocalDocs AI Assistant — Frontend

React + Vite UI for the LocalDocs AI Assistant. Talks to the FastAPI backend (`../backend/`) over REST — all RAG/LLM logic lives on the backend; this app only handles UI, file upload, requests, and rendering responses.

## Setup

```bash
npm install
cp .env.example .env   # set VITE_API_URL if the backend isn't on localhost:8000
npm run dev
```

Opens at `http://localhost:5173`.

## Build

```bash
npm run build      # outputs to dist/
npm run preview    # serve the production build locally
```

## Environment variables

| Variable | Description |
|---|---|
| `VITE_API_URL` | Base URL of the FastAPI backend, no trailing slash (e.g. `http://localhost:8000`) |

See the repository root `README.md` for the full project architecture, Docker Compose, and Cloud deployment instructions.
