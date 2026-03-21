-- Schema per ARSA (Autonomous Research & Synthesis Agent)

-- Tabella delle sessioni di ricerca (per gestire ricerche multiple parallele o storiche)
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    topic TEXT NOT NULL,
    purpose TEXT NOT NULL,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabella degli URL visitati per evitare duplicati e loop
CREATE TABLE IF NOT EXISTS crawled_urls (
    url_hash TEXT PRIMARY KEY, -- MD5/SHA256 dell'URL
    url TEXT NOT NULL,
    session_id TEXT,
    depth INTEGER DEFAULT 0,
    content_hash TEXT, -- Per de-duplicazione basata sul contenuto (anti-boilerplate)
    relevance_score FLOAT,
    crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

-- Tabella delle entità estratte (Ontologia dinamica)
CREATE TABLE IF NOT EXISTS entities (
    entity_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    name TEXT NOT NULL,
    entity_type TEXT, -- Concept, Person, Tech, etc.
    frequency INTEGER DEFAULT 1,
    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id),
    UNIQUE(session_id, name)
);

-- Tabella del Gap Analysis e Query Expansion
CREATE TABLE IF NOT EXISTS research_steps (
    step_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    gap_description TEXT,
    suggested_queries TEXT, -- JSON string delle nuove query generate
    saturation_score FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);
