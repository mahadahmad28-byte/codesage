# 🧠 CodeSage — AI Codebase Q&A Agent

> **Upload any GitHub repo. Ask questions about it in plain English.**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://reactjs.org)
[![Gemini](https://img.shields.io/badge/Gemini_API-2.0_Flash-4285F4?logo=google&logoColor=white)](https://aistudio.google.com)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Store-orange)](https://trychroma.com)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## 🎬 What It Does

CodeSage indexes any GitHub repository and lets you **chat with the codebase**:

- *"How does authentication work in this project?"*
- *"Explain the database models"*
- *"Where are API routes defined and what do they do?"*
- *"What testing strategy does this repo use?"*

Responses stream in real-time with **source citations** linking to exact files and line numbers.

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────┐
│              Frontend (React + Vite)                          │
│  Vercel · http://localhost:5173                               │
│                                                              │
│  ┌─────────────┐  ┌─────────────────┐  ┌──────────────────┐ │
│  │  RepoInput  │  │   ChatWindow    │  │    FileTree      │ │
│  │  Switcher   │  │  (SSE Stream)   │  │  + ExplainPanel  │ │
│  └──────┬──────┘  └───────┬─────────┘  └────────┬─────────┘ │
└─────────┼─────────────────┼────────────────────┼─────────────┘
          │  POST /api/ingest│ POST /api/chat/stream│ POST /api/explain
          ▼                  ▼                     ▼
┌──────────────────────────────────────────────────────────────┐
│              Backend (FastAPI · Python 3.11)                  │
│  Render Free Tier · http://localhost:8000                     │
│                                                              │
│  ┌──────────────┐  ┌─────────────┐  ┌────────────────────┐  │
│  │ Repo Loader  │  │  RAG Engine │  │   Explain File     │  │
│  │ (GitPython)  │  │ (Retrieve → │  │   (Full file AI    │  │
│  │ clone/pull   │  │  Augment →  │  │    summary, SSE)   │  │
│  │ filter files │  │  Generate)  │  └────────────────────┘  │
│  └──────┬───────┘  └──────┬──────┘                          │
│         │                 │                                  │
│    ┌────▼─────┐    ┌──────▼────────┐                        │
│    │ Chunker  │    │ Vector Store  │   ┌──────────────────┐  │
│    │ (line +  │    │  (ChromaDB)   │   │   Gemini API     │  │
│    │  AST)    │    │  persistent   │   │  text-embedding  │  │
│    └──────────┘    └───────────────┘   │  -004 + 2.0 Flash│  │
│                                        └──────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔍 **RAG Q&A** | Ask anything about the codebase; answers cite exact files + lines |
| ⚡ **Streaming** | Responses stream in real-time via Server-Sent Events |
| 🗄️ **Multi-repo** | Index multiple repos, switch between them in the sidebar |
| 🌲 **File Tree** | Collapsible explorer with emoji icons per language |
| 🔍 **Explain File** | Double-click any file to get a streaming AI explanation |
| 💬 **Chat History** | Follow-up questions maintain conversation context |
| 🎨 **Dark UI** | Premium glassmorphism-inspired interface |

---

## 🚀 Quick Start (Local)

### Prerequisites
- Python 3.11+
- Node.js 18+
- A free [Gemini API key](https://aistudio.google.com)

### 1 — Backend

```bash
cd codesage

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux

# Install dependencies
pip install -e .

# Configure API key
copy .env.example .env
# Edit .env and set: GEMINI_API_KEY=your_key_here

# Start backend
python -m backend.main
# → http://localhost:8000
# → http://localhost:8000/docs  (interactive API docs)
```

### 2 — Frontend

```bash
cd codesage/frontend

npm install
npm run dev
# → http://localhost:5173
```

### 3 — Use It

1. Open **http://localhost:5173**
2. Paste a GitHub repo URL (e.g. `https://github.com/tiangolo/fastapi`)
3. Click ⚡ to index it (takes 30–90 seconds for first-time)
4. Ask questions in the chat!

---

## 🌐 Deploy (Free, 5 Minutes)

### Backend → Render

1. Push this repo to GitHub
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect your GitHub repo — Render auto-detects `render.yaml`
4. Add environment variable: `GEMINI_API_KEY = your_key`
5. Deploy! (Free tier, spins up in ~30s after inactivity)

### Frontend → Vercel

```bash
cd frontend
npx vercel --prod
# Follow prompts, set VITE_API_URL to your Render backend URL
```

Or connect directly via [vercel.com](https://vercel.com) dashboard.

---

## 📡 API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /health` | GET | Health check |
| `/api/ingest` | POST | Clone & index a GitHub repo |
| `/api/chat/stream` | POST | Stream Q&A answer (SSE) |
| `/api/explain` | POST | Stream file explanation (SSE) |
| `/api/repos` | GET | List all indexed repos |
| `/api/repos/{id}` | DELETE | Delete a repo |
| `/api/repos/{id}/tree` | GET | Get file tree |
| `/docs` | GET | Interactive Swagger UI |

---

## 📂 Project Structure

```
codesage/
├── backend/
│   ├── main.py               # FastAPI app, CORS, router registration
│   ├── models/schemas.py     # Pydantic request/response models
│   ├── routers/
│   │   ├── ingest.py         # POST /api/ingest — clone & index
│   │   ├── chat.py           # POST /api/chat/stream — SSE Q&A
│   │   ├── explain.py        # POST /api/explain — file explanation
│   │   └── filetree.py       # GET /api/repos/{id}/tree
│   └── services/
│       ├── repo_loader.py    # Git clone, file filtering, tree builder
│       ├── chunker.py        # Smart line/AST-aware code chunking
│       ├── embedder.py       # Gemini text-embedding-004 (768-dim)
│       ├── vector_store.py   # ChromaDB cosine-similarity wrapper
│       └── rag_engine.py     # RAG pipeline + explain_file() function
├── frontend/
│   ├── src/
│   │   ├── App.jsx           # Root layout
│   │   ├── components/
│   │   │   ├── ChatWindow.jsx    # SSE streaming + markdown + hljs
│   │   │   ├── RepoInput.jsx     # URL input + indexing status
│   │   │   ├── RepoSwitcher.jsx  # Multi-repo switcher
│   │   │   ├── FileTree.jsx      # Collapsible file explorer
│   │   │   ├── CitationChips.jsx # Source reference chips
│   │   │   └── ExplainPanel.jsx  # "Explain this file" modal
│   │   └── styles/index.css  # Dark design system + tokens
│   ├── vite.config.js        # Dev proxy → localhost:8000
│   └── vercel.json           # Production routing config
├── render.yaml               # Render.com deploy config
├── docker-compose.yml        # Full stack with one command
├── Dockerfile
└── .env.example
```

---

## 🛠️ Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| **LLM** | Gemini 2.5 Flash | Fast, free tier, thinking mode, great at code |
| **Embeddings** | Gemini `text-embedding-004` | 768-dim, retrieval-optimized |
| **Vector DB** | ChromaDB | In-process, no extra server needed |
| **Backend** | FastAPI + Python 3.11 | Async, type-safe, auto-docs |
| **Frontend** | React + Vite | Fast HMR, modern tooling |
| **Streaming** | Server-Sent Events | Real-time token streaming |
| **Syntax** | highlight.js + marked | Code rendering in chat |
| **Deployment** | Render + Vercel | Both have free tiers |

---

## 📊 How RAG Works in CodeSage

```
User question
      │
      ▼
Generate query embedding (Gemini text-embedding-004, RETRIEVAL_QUERY)
      │
      ▼
ChromaDB cosine similarity search → top 8 code chunks
      │
      ▼
Build context: "[Source 1: auth.py L42-67] def login(): ..."
      │
      ▼
Augmented prompt → Gemini 2.0 Flash (streaming)
      │
      ▼
Streamed answer with file/line citations → Frontend
```

---

## 🔒 Security Notes

- The `.env` file is gitignored — never commit your API key
- Set `CORS allow_origins` to your specific domain in production
- Use Render's secret environment variables for the API key
- ChromaDB data persists to disk; back it up if using production data

---

## 🗺️ Roadmap

- [x] RAG pipeline with source citations
- [x] SSE streaming responses
- [x] Multi-repo support (persistent metadata)
- [x] File tree explorer
- [x] "Explain this file" mode
- [x] CI/CD with GitHub Actions
- [x] Support for private repos (GitHub token)
- [ ] Authentication (protect your instance)
- [ ] PDF export of conversations

---

*Built as a portfolio project by a CS student — demonstrates RAG, vector search, and full-stack development.*
