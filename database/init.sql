CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS bylaws (
    id SERIAL PRIMARY KEY,
    section TEXT NOT NULL,
    subsection TEXT NOT NULL DEFAULT '',
    title TEXT NOT NULL,
    chapter TEXT NOT NULL DEFAULT '',
    topic TEXT NOT NULL,
    topic_group TEXT,
    issue_category TEXT,
    keywords TEXT[] NOT NULL,
    technical_terms TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    layman_keywords TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    content TEXT NOT NULL,
    explanation TEXT NOT NULL,
    plain_english TEXT NOT NULL DEFAULT '',
    why_this_applies TEXT NOT NULL DEFAULT '',
    real_world_example TEXT NOT NULL DEFAULT '',
    official_excerpt TEXT NOT NULL DEFAULT '',
    normalized_legal_text TEXT NOT NULL DEFAULT '',
    source_grounded_official_text TEXT NOT NULL DEFAULT '',
    official_grounding_status TEXT NOT NULL DEFAULT '',
    primary_retrieval_text TEXT NOT NULL DEFAULT '',
    retrieval_text TEXT NOT NULL DEFAULT '',
    common_disputes TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    example_queries TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    applicable_when TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    trigger_conditions TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    not_applicable_when TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    issue_patterns TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    recommended_next_steps TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    documents_to_collect TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    authority_to_approach TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    example TEXT NOT NULL,
    conditions_required JSONB NOT NULL DEFAULT '[]'::jsonb,
    possible_challenges TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    related_statutes TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    embedding VECTOR(384),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (section, subsection, title)
);

CREATE TABLE IF NOT EXISTS bylaw_relations (
    id SERIAL PRIMARY KEY,
    source_section TEXT NOT NULL,
    source_subsection TEXT NOT NULL DEFAULT '',
    target_section TEXT NOT NULL,
    target_subsection TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS bylaws_embedding_idx
    ON bylaws USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS idx_bylaws_section_subsection
    ON bylaws (section, subsection);

CREATE INDEX IF NOT EXISTS idx_bylaws_topic
    ON bylaws (topic);

CREATE INDEX IF NOT EXISTS idx_bylaws_topic_group
    ON bylaws (topic_group);

CREATE INDEX IF NOT EXISTS idx_bylaws_issue_category
    ON bylaws (issue_category);

CREATE INDEX IF NOT EXISTS idx_bylaws_chapter
    ON bylaws (chapter);

CREATE INDEX IF NOT EXISTS idx_bylaw_relations_source
    ON bylaw_relations (source_section, source_subsection);
