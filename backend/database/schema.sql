CREATE TABLE analyses (
    id UUID PRIMARY KEY,
    entity TEXT NOT NULL,
    country TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    language VARCHAR(8) NOT NULL DEFAULT 'en',
    sources TEXT[] NOT NULL,
    status TEXT NOT NULL,
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE source_items (
    id UUID PRIMARY KEY,
    analysis_id UUID NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    source TEXT NOT NULL,
    text_excerpt TEXT NOT NULL,
    title TEXT,
    author TEXT,
    url TEXT,
    published_at TIMESTAMPTZ NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE sentiment_results (
    item_id UUID PRIMARY KEY REFERENCES source_items(id) ON DELETE CASCADE,
    label TEXT NOT NULL,
    positive_score NUMERIC(5, 4) NOT NULL,
    neutral_score NUMERIC(5, 4) NOT NULL,
    negative_score NUMERIC(5, 4) NOT NULL,
    key_phrases TEXT[] NOT NULL DEFAULT '{}'
);

CREATE TABLE event_annotations (
    id BIGSERIAL PRIMARY KEY,
    analysis_id UUID NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    event_date DATE NOT NULL,
    title TEXT NOT NULL,
    source TEXT NOT NULL,
    url TEXT,
    tone NUMERIC(8, 4)
);

CREATE TABLE aggregate_snapshots (
    analysis_id UUID PRIMARY KEY REFERENCES analyses(id) ON DELETE CASCADE,
    snapshot JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE uploaded_files (
    id UUID PRIMARY KEY,
    analysis_id UUID NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    row_count INTEGER NOT NULL,
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_source_items_analysis_date ON source_items (analysis_id, published_at);
CREATE INDEX idx_source_items_source ON source_items (source);
CREATE INDEX idx_sentiment_results_label ON sentiment_results (label);

