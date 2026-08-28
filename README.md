# Tenant Rights Helper: backend

Answers tenant questions about Ontario's *Residential Tenancies Act, 2006* using only the text of the Act, with section citations. The Act is stored in PostgreSQL with pgvector, and Claude writes the answers from the sections retrieved for each question.

## Stack

Python 3.12+, FastAPI, PostgreSQL 16 + pgvector, SQLAlchemy, Alembic, fastembed (`bge-small-en-v1.5`), pymupdf4llm, Claude API.

## Setup

You need Docker, [uv](https://docs.astral.sh/uv/) and an Anthropic API key.

```bash
cp .env.example .env              # set your passwords, ANTHROPIC_API_KEY and CLAUDE_MODEL
docker compose up -d              # Postgres with pgvector, plus the api/ingest users
uv sync
uv run alembic upgrade head       # create the tables
```

Download the Act as a PDF from [e-Laws](https://www.ontario.ca/laws/statute/06r17) and save it as `data/raw/ON/rta-2006.pdf`.

## Usage

```bash
uv run python -m ingestion.pipeline                 # parse, chunk, embed and store the Act
uv run python -m ingestion.pipeline --force         # redo it even if the PDF hasn't changed
uv run uvicorn app.main:app --reload --port 8080    # API on http://localhost:8080
```

Interactive API docs are at `http://localhost:8080/docs`.

## API

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Health check |
| GET | `/api/jurisdictions` | Supported provinces |
| POST | `/api/search` | Returns the chunks closest to a question |
| POST | `/api/chat` | Streams an answer from Claude as server-sent events |

`/api/chat` takes `{"question": "...", "jurisdiction": "ON"}` and streams these events:

- `token`: the next piece of the answer
- `citations`: the sections the answer cites
- `declined`: