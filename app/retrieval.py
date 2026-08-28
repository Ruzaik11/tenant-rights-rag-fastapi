from dataclasses import dataclass

import sqlalchemy as sa

from app.db.session import api_engine
from app.db.tables import chunks
from app.embeddings.embedder import embed_query
from app.db.tables import chunks, sources

@dataclass
class SearchResult:
    id: str
    section: str
    heading: str
    text: str
    page_start: int
    page_end: int
    source_title: str
    source_url: str | None
    similarity: float


def vector_search(question: str, jurisdiction: str, limit: int = 5) -> list[SearchResult]:
    distance = chunks.c.embedding.cosine_distance(embed_query(question)).label("distance")
    query = (
        sa.select(
            chunks.c.id,
            chunks.c.section,
            chunks.c.heading,
            chunks.c.text,
            chunks.c.page_start,
            chunks.c.page_end,
            distance,
            sources.c.title,
            sources.c.url,
        )
        .join(sources, sources.c.id == chunks.c.source_id)
        .where(chunks.c.jurisdiction == jurisdiction)
        .order_by(distance)
        .limit(limit)
    )
    with api_engine().connect() as conn:
        rows = conn.execute(query).all()

    return [
        SearchResult(
            id=row.id,
            section=row.section,
            heading=row.heading,
            text=row.text,
            page_start=row.page_start,
            page_end=row.page_end,
            source_title=row.title,
            source_url=row.url,
            similarity=round(1 - row.distance, 3),
        )
        for row in rows
    ]