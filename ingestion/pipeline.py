import hashlib
import logging
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import sqlalchemy as sa

from app.core.config import settings
from app.db.session import ingest_engine
from app.db.tables import chunks as chunks_table
from app.db.tables import sources as sources_table
from app.embeddings.embedder import embed_passages
from ingestion.chunker import build_chunks
from ingestion.parsers import ontario_rta

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Source:
    id: str
    jurisdiction: str
    title: str
    source_type: str
    url: str
    pdf_path: Path
    version_date: date | None = None


ONTARIO_RTA = Source(
    id="ON-RTA2006",
    jurisdiction="ON",
    title="Residential Tenancies Act, 2006",
    source_type="statute",
    url="https://www.ontario.ca/laws/statute/06r17",
    pdf_path=settings.raw_dir / "ON" / "rta-2006.pdf",
    version_date=None,  # the "current version" date shown on e-Laws for this PDF
)


def ingest(source: Source, force: bool = False) -> int:
    """Parse, chunk and embed a source and replace its rows in the database.

    Returns the number of chunks saved, or 0 if the file hasn't changed since the last run.
    """
    engine = ingest_engine()
    file_hash = sha256(source.pdf_path)

    with engine.connect() as conn:
        stored_hash = conn.scalar(
            sa.select(sources_table.c.file_sha256).where(sources_table.c.id == source.id)
        )
    if stored_hash == file_hash and not force:
        log.info("%s is unchanged since the last ingest, skipping", source.id)
        return 0

    started = time.perf_counter()

    def elapsed() -> str:
        return f"{time.perf_counter() - started:.0f}s"

    sections = ontario_rta.parse(source.pdf_path)
    log.info("Parsed %d sections (%s)", len(sections), elapsed())

    chunks = build_chunks(sections, source.id, source.title)
    log.info("Split into %d chunks (%s)", len(chunks), elapsed())

    vectors = embed_passages([chunk.text for chunk in chunks])
    log.info("Embedded %d chunks (%s)", len(vectors), elapsed())

    rows = [
        {
            "id": chunk.id,
            "source_id": source.id,
            "jurisdiction": source.jurisdiction,
            "section": chunk.section,
            "heading": chunk.heading,
            "part": chunk.part,
            "page_start": chunk.page_start,
            "page_end": chunk.page_end,
            "text": chunk.text,
            "tokens": chunk.tokens,
            "embedding": vector,
        }
        for chunk, vector in zip(chunks, vectors)
    ]

    # Replace the old version in one transaction, so a failed run leaves the previous data in place
    with engine.begin() as conn:
        conn.execute(sa.delete(sources_table).where(sources_table.c.id == source.id))
        conn.execute(
            sa.insert(sources_table),
            {
                "id": source.id,
                "jurisdiction": source.jurisdiction,
                "title": source.title,
                "source_type": source.source_type,
                "url": source.url,
                "version_date": source.version_date,
                "file_sha256": file_hash,
            },
        )
        conn.execute(sa.insert(chunks_table), rows)

    log.info("Saved %d chunks (%s)", len(rows), elapsed())
    return len(rows)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Load the Ontario RTA into the database")
    parser.add_argument("--force", action="store_true", help="re-ingest even if the PDF is unchanged")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ingest(ONTARIO_RTA, force=args.force)