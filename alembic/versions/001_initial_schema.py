"""Create initial schema: bylaws + bylaw_relations + schema_version

Revision ID: 001
Revises:
Create Date: 2026-05-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "schema_version",
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("applied_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "bylaws",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("section", sa.Text(), nullable=False),
        sa.Column("subsection", sa.Text(), nullable=False, server_default=""),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("chapter", sa.Text(), nullable=False, server_default=""),
        sa.Column("topic", sa.Text(), nullable=False),
        sa.Column("topic_group", sa.Text(), nullable=True),
        sa.Column("issue_category", sa.Text(), nullable=True),
        sa.Column("keywords", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("technical_terms", postgresql.ARRAY(sa.Text()),
                  nullable=False, server_default="{}"),
        sa.Column("layman_keywords", postgresql.ARRAY(sa.Text()),
                  nullable=False, server_default="{}"),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("plain_english", sa.Text(), nullable=False, server_default=""),
        sa.Column("why_this_applies", sa.Text(), nullable=False, server_default=""),
        sa.Column("real_world_example", sa.Text(), nullable=False, server_default=""),
        sa.Column("official_excerpt", sa.Text(), nullable=False, server_default=""),
        sa.Column("normalized_legal_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("source_grounded_official_text", sa.Text(),
                  nullable=False, server_default=""),
        sa.Column("official_grounding_status", sa.Text(),
                  nullable=False, server_default=""),
        sa.Column("primary_retrieval_text", sa.Text(),
                  nullable=False, server_default=""),
        sa.Column("retrieval_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("common_disputes", postgresql.ARRAY(sa.Text()),
                  nullable=False, server_default="{}"),
        sa.Column("example_queries", postgresql.ARRAY(sa.Text()),
                  nullable=False, server_default="{}"),
        sa.Column("applicable_when", postgresql.ARRAY(sa.Text()),
                  nullable=False, server_default="{}"),
        sa.Column("trigger_conditions", postgresql.ARRAY(sa.Text()),
                  nullable=False, server_default="{}"),
        sa.Column("not_applicable_when", postgresql.ARRAY(sa.Text()),
                  nullable=False, server_default="{}"),
        sa.Column("issue_patterns", postgresql.ARRAY(sa.Text()),
                  nullable=False, server_default="{}"),
        sa.Column("recommended_next_steps", postgresql.ARRAY(sa.Text()),
                  nullable=False, server_default="{}"),
        sa.Column("documents_to_collect", postgresql.ARRAY(sa.Text()),
                  nullable=False, server_default="{}"),
        sa.Column("authority_to_approach", postgresql.ARRAY(sa.Text()),
                  nullable=False, server_default="{}"),
        sa.Column("example", sa.Text(), nullable=False),
        sa.Column("conditions_required",
                  postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("possible_challenges", postgresql.ARRAY(sa.Text()),
                  nullable=False, server_default="{}"),
        sa.Column("related_statutes", postgresql.ARRAY(sa.Text()),
                  nullable=False, server_default="{}"),
        sa.Column("embedding", Vector(384), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False,
                  server_default=sa.func.now()),
        sa.UniqueConstraint("section", "subsection", "title"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("bylaws_embedding_idx", "bylaws", ["embedding"],
                    postgresql_using="hnsw",
                    postgresql_with={"m": 16, "ef_construction": 200},
                    postgresql_ops={"embedding": "vector_cosine_ops"})
    op.create_index("idx_bylaws_section_subsection", "bylaws",
                    ["section", "subsection"])
    op.create_index("idx_bylaws_topic", "bylaws", ["topic"])
    op.create_index("idx_bylaws_topic_group", "bylaws", ["topic_group"])
    op.create_index("idx_bylaws_issue_category", "bylaws", ["issue_category"])
    op.create_index("idx_bylaws_chapter", "bylaws", ["chapter"])

    op.create_table(
        "bylaw_relations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_section", sa.Text(), nullable=False),
        sa.Column("source_subsection", sa.Text(), nullable=False, server_default=""),
        sa.Column("target_section", sa.Text(), nullable=False),
        sa.Column("target_subsection", sa.Text(), nullable=False, server_default=""),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_bylaw_relations_source", "bylaw_relations",
                    ["source_section", "source_subsection"])

    op.create_table(
        "query_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("returned_rule", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False,
                  server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    op.execute("INSERT INTO schema_version (version) VALUES (2)")


def downgrade() -> None:
    op.drop_table("query_logs")
    op.drop_table("bylaw_relations")
    op.drop_table("bylaws")
    op.drop_table("schema_version")
    op.execute("DROP EXTENSION IF EXISTS vector")
