
# 📚 Adaptive Learning Platform – Backend

A robust FastAPI backend for an adaptive e-learning platform, featuring Google OAuth2 authentication, document upload and processing, MCQ/quiz generation with LLMs, RAG-based semantic search, study mode, streaks, and more. Integrates with PostgreSQL, Redis, MinIO, and Qdrant for scalable, high-performance operations.

---

## 📑 Table of Contents

- [Project Overview](#project-overview)
- [Features](#features)
- [Architecture](#architecture)
- [Setup Guide](#setup-guide)
- [Environment Variables](#environment-variables)
- [Core Modules & Folders](#core-modules--folders)
- [License](#license)

---

## Project Overview

This backend powers an adaptive learning platform, supporting personalized study experiences, document management, quiz generation, and advanced search. It is designed for scalability, modularity, and easy integration with modern frontend frameworks.

---

## Features

- **User Authentication:** Google OAuth2 login, JWT-based sessions.
- **Document Upload & Processing:** Supports PDF, PPTX, DOCX, TXT; automatic conversion and metadata extraction.
- **Quiz/MCQ Generation:** Uses LLMs (OpenAI, Groq, DeepSeek, etc.) for dynamic question generation, with explanations and difficulty control.
- **RAG Search:** Retrieval-Augmented Generation for semantic search across user documents.
- **Study Mode:** Interactive chat, learning tools, progress tracking, and document streaming.
- **Streaks & Leaderboards:** Gamified learning with streak tracking and leaderboards.
- **Library Search:** Fast, relevant search across user-uploaded content.
- **File Downloads:** Generate and download quizzes as PDF or DOCX.
- **Caching:** Redis for model and metadata caching.
- **Vector Search:** Qdrant for high-performance semantic search.
- **MinIO Integration:** S3-compatible storage for user files.

---

## Architecture

- **FastAPI**: Main web framework for API endpoints.
- **PostgreSQL**: Primary database for users, quizzes, documents, and metadata.
- **Redis**: Caching for models and document metadata.
- **MinIO**: S3-compatible storage for uploaded files.
- **Qdrant**: Vector database for semantic search and RAG.
- **LLM Providers**: OpenAI, Groq, DeepSeek, HuggingFace, etc. (API key rotation supported).

```
[User] ⇄ [FastAPI Backend]
   ├─ Auth (Google OAuth2)
   ├─ Document Upload/Download
   ├─ Quiz/MCQ Generation (LLMs)
   ├─ RAG Search (Qdrant)
   ├─ Study Mode (Chat, Progress)
   ├─ Streaks/Leaderboard
   ├─ Library Search
   ├─ File Storage (MinIO)
   └─ Caching (Redis)
```

---

## Setup Guide

### 1. Clone the Repository

```bash
git clone https://github.com/abdullah270602/Adaptive-E-Learning-Platform-Bakend
cd Adaptive-E-Learning-Platform-Bakend
```

### 2. Install Dependencies (Recommended: `uv`)

- Install [`uv`](https://github.com/astral-sh/uv):
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- Create and activate a virtual environment:
  ```bash
  uv venv
  # Linux/macOS:
  source .venv/bin/activate
  # Windows:
  .venv\Scripts\activate
  ```
- Install dependencies:
  ```bash
  uv sync
  ```

### 3. Install LibreOffice (for document conversion)

- **Linux:**
  ```bash
  sudo apt update
  sudo apt install libreoffice -y
  libreoffice --version
  ```
- **Windows:**
  1. Download from [libreoffice.org](https://www.libreoffice.org/download/download/)
  2. Install and add `C:\Program Files\LibreOffice\program` to your PATH
  3. Use `soffice.com --version` to verify

> ⚠️ On Windows, the correct CLI binary is usually `soffice.com`, not `libreoffice`.

### 4. Configure Environment Variables

- Copy `.env.example` to `.env` and fill in required values (see below).

### 5. Run the Application

```bash
uvicorn main:app --reload
```

- Access API docs at: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## Environment Variables

- `SESSION_SECRET_KEY`: Secret for session middleware
- `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_NAME`: PostgreSQL config
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASS`: Redis config
- `MINIO_BUCKET_NAME`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_ENDPOINT`: MinIO config
- `QDRANT_URL`, `QDRANT_API_KEY`: Qdrant vector DB config
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`: Google OAuth2
- `OPENAI_API_KEY`, `GROQ_API_KEY`, `DEEPSEEK_API_KEY`, etc.: LLM API keys
- `WINDOWS_SOFFICE_PATH`, `LINUX_SOFFICE_PATH`: LibreOffice CLI paths

> ⚠️ You can see .evn.example for reference.

## Core Modules & Folders

- `main.py` – FastAPI app, middleware, router registration
- `app/routes/` – All API endpoints (auth, file, quiz, study, etc.)
- `app/services/` – Business logic (MCQ gen, RAG, file processing, etc.)
- `app/database/` – PostgreSQL queries and connection management
- `app/schemas/` – Pydantic models for request/response validation
- `app/cache/` – Redis caching for models and metadata
- `app/constants.py` – Global constants (CORS, model IDs, etc.)

---


## Troubleshooting

- **Database Connection Issues:** Check `.env` for correct DB credentials and network access.
- **Redis/MinIO/Qdrant Errors:** Ensure services are running and accessible at configured endpoints.
- **OAuth2 Issues:** Verify Google credentials and redirect URIs.
- **Document Conversion Fails:** Ensure LibreOffice is installed and CLI path is set in `.env`.
- **LLM API Errors:** Check API key validity and usage limits.

---

## License

MIT License. See [LICENSE](LICENSE) for details.

---

> For questions, issues, or contributions, please open an issue or pull request on GitHub.

