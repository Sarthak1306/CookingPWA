CREATE TABLE recipe (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT NOT NULL,
    base_servings   INTEGER NOT NULL DEFAULT 2,
    source          TEXT NOT NULL DEFAULT 'llm',
    cuisine         TEXT NOT NULL DEFAULT '',
    est_minutes     INTEGER,
    keeps_well      INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- Whether a recipe_ingredient is "have" or "missing" is deliberately not
-- stored here — the pantry can change after a recipe is saved, so it's
-- always recomputed live against the current pantry when a recipe is read.
CREATE TABLE recipe_ingredient (
    recipe_id       INTEGER NOT NULL REFERENCES recipe(id) ON DELETE CASCADE,
    ingredient_id   INTEGER NOT NULL REFERENCES canonical_ingredient(id),
    qty             TEXT NOT NULL DEFAULT '',
    unit            TEXT NOT NULL DEFAULT '',
    optional_flag   INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (recipe_id, ingredient_id)
);

CREATE TABLE recipe_step (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe_id       INTEGER NOT NULL REFERENCES recipe(id) ON DELETE CASCADE,
    position        INTEGER NOT NULL,
    text            TEXT NOT NULL,
    timer_seconds   INTEGER
);

CREATE INDEX idx_recipe_step_recipe_id ON recipe_step(recipe_id);

-- Single row, hand-editable in P5. Seeded once with the spec's seed text so
-- get_taste_profile() has something real to read from P2 onward.
CREATE TABLE taste_profile (
    id          INTEGER PRIMARY KEY CHECK (id = 1),
    body_text   TEXT NOT NULL,
    updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

INSERT INTO taste_profile (id, body_text) VALUES (1,
    'Leans towards Indian food — curries, rice dishes, dal, paneer — and also makes Mexican-style wraps and sandwiches. Main proteins are chicken, paneer, and eggs. This is a preference, not a restriction: suggest recipes from any cuisine when they''re genuinely good, and don''t hesitate to introduce something new. The one hard rule is no seafood, no beef, no pork, ever. Happy to spend up to an hour cooking and open to batch recipes that hold for a few days. Assume a normal home kitchen with no specialist equipment. The pantry records what he has, not how much — assume a usable amount of anything listed unless it''s flagged as running low.'
);

CREATE TABLE job (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    kind        TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'pending',
    result_json TEXT,
    error       TEXT,
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX idx_job_status ON job(status);
CREATE INDEX idx_job_kind_created_at ON job(kind, created_at);

-- Spend guard: one row per actual OpenRouter call (not per suggest job —
-- a single suggest job's tool loop can make several). The monthly count of
-- this table is the hard cap check, so a stuck retry loop can't quietly
-- drain the balance overnight.
CREATE TABLE llm_call (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX idx_llm_call_created_at ON llm_call(created_at);
