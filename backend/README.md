# LibraryPortal — Backend

FastAPI backend for the University Library Portal.

## Tech Stack

- Python
- FastAPI
- SQLAlchemy
- Alembic
- Neon PostgreSQL

## Getting Started

1. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Copy the environment file and fill in values:

   ```bash
   cp .env.example .env
   ```

4. Run the development server:

   ```bash
   uvicorn app.main:app --reload
   ```

5. Open [http://localhost:8000/health](http://localhost:8000/health) to verify the API is running.

## Architecture

```
Next.js 14
     │
     │ HTTP/REST API
     ▼
FastAPI
     │
     ├──────────────► Recommendation Model
     │
     ├──────────────► Transformer + LLM
     │
     ▼
Neon PostgreSQL
```

The frontend never connects directly to Neon. All database access goes through this backend.
