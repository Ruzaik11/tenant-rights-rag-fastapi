"""create sources and chunks

Revision ID: 2d840802638c
Revises:
"""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import TSVECTOR

revision = "2d840802638c"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sources",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("jurisdiction", sa.String(2), nullable=False),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("source_type", sa.Text, nullable=False),
        sa.Column("url", sa.Text),
        sa.Column("version_date", sa.Date),
        sa.Column("file_sha256", sa.String(64), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "chunks",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("source_id", sa.Text, sa.ForeignKey("sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("jurisdiction", sa.String(2), nullable=False),
        sa.Column("section", sa.Text, nullable=False),
        sa.Column("heading", sa.Text, nullable=False),
        sa.Column("part", sa.Text, nullable=False, server_default=""),
        sa.Column("page_start", sa.Integer, nullable=False),
        sa.Column("page_end", sa.Integer, nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("tokens", sa.Integer, nullable=False),
        sa.Column("embedding", Vector(384), nullable=False),
        sa.Column(
            "search",
            TSVECTOR,
            sa.Computed("to_tsvector('english', heading || ' ' || text)", persisted=True),
        ),
    )

    op.create_index("ix_chunks_jurisdiction", "chunks", ["jurisdiction"])
    op.create_index("ix_chunks_search", "chunks", ["search"], postgresql_using="gin")
    op.create_index(
        "ix_chunks_embedding",
        "chunks",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def downgrade() -> None:
    op.drop_table("chunks")
    op.drop_table("sources")
