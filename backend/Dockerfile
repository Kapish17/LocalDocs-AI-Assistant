# LocalDocs AI Assistant — FastAPI backend container image.
#
# Build context is the repository ROOT (not backend/), because the image
# also needs data/ to build its knowledge base from at startup:
#   docker build -f backend/Dockerfile -t localdocs-backend .
# (docker-compose.yml at the repo root already does this.)
#
# Built for Google Cloud Run: listens on 0.0.0.0 and reads the PORT env
# var Cloud Run injects at runtime (falls back to 8080 for local `docker run`).

FROM python:3.12-slim

WORKDIR /app

# System libraries needed by opencv-python-headless / pymupdf / torch at
# runtime (kept minimal — no compilers or dev headers).
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first so this layer is cached across code-only
# changes. requirements-docker.txt is a slim, Docker-only dependency list
# (derived from reading the actual backend/ imports, not copied from
# requirements.txt) that drops streamlit, docx2txt, and beautifulsoup4 -
# none of which any backend module actually imports. See that file's
# header comment for the full rationale.
COPY backend/requirements-docker.txt requirements.txt

# torch AND torchvision are installed together, pinned to an exact matching
# pair, and only from the CPU-only PyTorch wheel index — so pip never
# resolves the default CUDA-enabled wheel (which pulls in several hundred
# MB of nvidia-* packages this container never uses; core/ocr.py's
# easyocr.Reader(..., gpu=False) already runs CPU-only).
#
# Installing them together, pinned, in one command is required, not just
# tidy: easyocr (in requirements.txt below) depends on torchvision for its
# text-detection model's NMS op. Installing torch alone here and letting
# `pip install -r requirements.txt` pull in torchvision afterward (as a
# transitive dependency of easyocr) resolves torchvision from the default
# PyPI index instead of the CPU index — same *version number*, but a
# different *build*, compiled against a different torch ABI. That mismatch
# is exactly what caused startup to fail with
# "RuntimeError: operator torchvision::nms does not exist" when
# rag/embeddings.py created HuggingFaceEmbeddings (transformers imports
# torchvision if it's present). Pinning both from the same index guarantees
# a matched, working pair; bump both together if you ever change one.
RUN pip install --no-cache-dir torch==2.14.0 torchvision==0.29.0 --index-url https://download.pytorch.org/whl/cpu

# sentence-transformers, transformers, easyocr, etc. (from requirements.txt,
# copied above) now see torch/torchvision already satisfied at the exact
# pinned versions and leave them alone.
RUN pip install --no-cache-dir -r requirements.txt

# Copy just the backend package (api/, core/, rag/, llm/, loaders/, utils/)
# to /app, so cwd == "backend root" inside the container, matching how
# api/main.py's imports and rag/core's relative data/database paths expect
# to be run. .dockerignore (repo root) keeps secrets and dev files out.
COPY backend/api ./api
COPY backend/core ./core
COPY backend/rag ./rag
COPY backend/llm ./llm
COPY backend/loaders ./loaders
COPY backend/utils ./utils

# Seed documents baked into the image so the container can build a
# knowledge base at startup (Cloud Run instances are stateless — see
# README "Google Cloud Run Deployment" for details). Optional: the app
# still starts fine with an empty/absent data/ and just returns 503 from
# /query and /upload until documents exist.
COPY data ./data

# Cloud Run sets PORT at runtime; 8080 is used for local `docker run` /
# testing when PORT isn't set.
ENV PORT=8080
EXPOSE 8080

# Shell form so ${PORT} is expanded at container start (Cloud Run assigns
# PORT dynamically — it is not known at build time).
CMD exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT}
