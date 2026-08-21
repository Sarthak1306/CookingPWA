CREATE TABLE canonical_ingredient (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    name                  TEXT NOT NULL UNIQUE,
    default_unit          TEXT NOT NULL DEFAULT '',
    category              TEXT NOT NULL,
    deny_flag             INTEGER NOT NULL DEFAULT 0,
    common_purchase_qty   TEXT NOT NULL DEFAULT '',
    common_purchase_unit  TEXT NOT NULL DEFAULT ''
);

CREATE TABLE pantry_item (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    ingredient_id  INTEGER NOT NULL UNIQUE REFERENCES canonical_ingredient(id),
    qty_label      TEXT NOT NULL DEFAULT '',
    is_low         INTEGER NOT NULL DEFAULT 0,
    updated_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX idx_canonical_ingredient_category ON canonical_ingredient(category);
