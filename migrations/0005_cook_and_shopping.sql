CREATE TABLE cook_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe_id   INTEGER NOT NULL REFERENCES recipe(id),
    cooked_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    rating      INTEGER,
    notes       TEXT
);

CREATE INDEX idx_cook_log_recipe_id ON cook_log(recipe_id);
CREATE INDEX idx_cook_log_cooked_at ON cook_log(cooked_at);

-- Existence of a row means "still need to buy" — P6's tick-off deletes the
-- row (and restocks the pantry) rather than flipping a status flag.
CREATE TABLE shopping_item (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ingredient_id INTEGER NOT NULL REFERENCES canonical_ingredient(id),
    added_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    added_from    TEXT NOT NULL DEFAULT 'manual'
);

CREATE INDEX idx_shopping_item_ingredient_id ON shopping_item(ingredient_id);
