from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from fastapi.responses import StreamingResponse
from app.chat import answer
from app.retrieval import SearchResult, vector_search

from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

app = FastAPI(title="Tenant Rights Canada")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

JURISDICTIONS = [
    {"code": "ON", "name": "Ontario", "tribunal": "Landlord and Tenant Board", "enabled": True},
    {"code": "NS", "name": "Nova Scotia", "tribunal": "Residential Tenancies Program", "enabled": False},
    {"code": "NB", "name": "New Brunswick", "tribunal": "Residential Tenancies Tribunal", "enabled": False},
]
ENABLED = {j["code"] for j in JURISDICTIONS if j["enabled"]}
TRIBUNALS = {j["code"]: j["tribunal"] for j in JURISDICTIONS}


class SearchRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    jurisdiction: str = "ON"
    limit: int = Field(default=5, ge=1, le=20)

class ChatRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    jurisdiction: str = "ON"


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/jurisdictions")
def jurisdictions() -> list[dict]:
    return JURISDICTIONS


@app.post("/api/search")
def search(request: SearchRequest) -> list[SearchResult]:
    if request.jurisdiction not in ENABLED:
        raise HTTPException(status_code=400, detail=f"{request.jurisdiction} is not supported yet")
    return vector_search(request.question.strip(), request.jurisdiction, request.limit)

@app.post("/api/chat")
def chat(request: ChatRequest) -> StreamingResponse:
    if request.jurisdiction not in ENABLED:
        raise HTTPException(status_code=400, detail=f"{request.jurisdiction} is not supported yet")
    events = answer(request.question.strip(), request.jurisdiction, TRIBUNALS[request.jurisdiction])
    return StreamingResponse(events, media_type="text/event-stream", headers={"Cache-Control": "no-cache"})