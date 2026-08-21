# Kitchen

Personal cooking assistant. Single user (Sarthak). Self-hosted on a VPS behind nginx at
`kitchen.sarthaksrivastava.tech`. Not a product, never deployed publicly, no other users.

Full design rationale lives in `docs/spec.md`. Read it before starting a phase. This file is the
short version plus the rules that must not be broken.

---

## Hard rules

**1. The app never does inventory arithmetic.**
The pantry tracks *what I have*, not *how much is left*. `pantry_item.qty_label` is free text I
wrote for myself ("500g bag", "half full"). Nothing subtracts from it, ever. Recipes match the
pantry on ingredient identity only. If you find yourself writing unit conversion, quantity
comparison, or stock decrementing — stop, you've misread the spec.

**2. Dietary restrictions are enforced in code, not just the prompt.**
Never seafood, beef, or pork. Every ingredient in an LLM response is checked against a deny list
before anything is saved or shown. A violation rejects the whole response and regenerates with the
violation named in the retry. This needs a test.

**3. Nothing is publicly accessible.**
Every route except `/login` and `/healthz` requires a valid session. There is no signup endpoint —
the user is created by a CLI script. Bind to `127.0.0.1:8420`, never `0.0.0.0`.

**4. Low friction beats correctness.**
Where a choice exists between an accurate flow and a fast one, take the fast one. This app dies the
moment it feels like data entry. No required fields beyond an ingredient name.

**5. Don't add features.**
Build the phase in front of you. If something seems missing, say so, don't build it. Explicitly out
of scope: expiry tracking, leftovers/cooked-portion tracking, nutrition, calories, multi-user,
meal calendars, social anything.

---

## Stack

- **Backend:** FastAPI, Python 3.12. Single process.
- **DB:** SQLite, one file on a mounted volume. Migrations from P0 — Alembic or numbered SQL files,
  never drop-and-recreate. There is real data in here from P1 onward.
- **Frontend:** Vite + React, `vite-plugin-pwa`. Built to `dist/`, served static by FastAPI.
- **LLM:** OpenRouter. Model name is a config value, not hardcoded at call sites.
- **Jobs:** SQLite `job` table + one asyncio worker in-process. No Redis, no Celery.
- **Auth:** argon2 password hash, session rows in SQLite, cookie `HttpOnly; Secure; SameSite=Lax`,
  one year expiry.
- **Deploy:** Docker Compose. nginx reverse-proxies the subdomain. certbot for TLS.

## Layout

```
app/            FastAPI — routes/, models/, llm/, auth/
web/            Vite + React frontend
migrations/     schema history
docs/spec.md    full design doc
fixtures/       canonical ingredient seed list
```

---

## How to work on this

**One phase per session.** Do not build ahead. Each phase should end with something that runs and
is committed.

| Phase | Deliverable |
|---|---|
| P0 | FastAPI skeleton, Docker, nginx subdomain, TLS, login, PWA installs on phone. Nothing else works. |
| P1 | Pantry CRUD with pack-size restocking and the running-low toggle. |
| P2 | Suggest + search via LLM tool-calling loop, with exclusions. |
| P3 | Cook a recipe, then the "what ran out?" checklist. |
| P4 | Steps + timers + cook mode. |
| P5 | Taste profile write-back loop. |
| P6 | Shopping list — manual adds, tick-off back into pantry. |

P0 exists specifically so deploy is never the scary unknown step later. Do it properly, get it live
on the phone, before writing any features.

**Before starting a phase:** state what you're going to build and what you're leaving out. Wait for
confirmation.

**Ask rather than assume.** If the spec doesn't cover something, ask. Do not invent an endpoint, a
table, or a UI flow and then build on it.

---

## Frontend — the Claude Design export

The UI is being designed in Claude Design and exported. When that export lands:

- **Treat the exported components as the visual source of truth.** Do not redesign, restyle, or
  "improve" them. Wire them to real API calls and real state.
- Keep the component structure. If a component needs data the API doesn't provide yet, say so
  rather than faking it or changing the design.
- The design assumes no inventory maths anywhere. If a component implies precise tracking, that's a
  bug in the design — flag it, don't implement it.

---

## Data model

```
user                 : id, username, password_hash, created_at
session              : id, user_id, token_hash, created_at, last_seen_at

canonical_ingredient : id, name, default_unit, category, deny_flag,
                       common_purchase_qty, common_purchase_unit
pantry_item          : id, ingredient_id, qty_label, is_low, updated_at

recipe               : id, title, base_servings, source, cuisine, est_minutes,
                       keeps_well, created_at
recipe_ingredient    : recipe_id, ingredient_id, qty, unit, optional_flag
recipe_step          : id, recipe_id, position, text, timer_seconds NULL

cook_log             : id, recipe_id, cooked_at, rating, notes
shopping_item        : id, ingredient_id, added_at, added_from
taste_profile        : id, body_text, updated_at
job                  : id, kind, payload_json, status, result_json, error
```

`recipe_ingredient` keeps qty and unit because recipes are *read* while cooking ("2 tbsp oil").
That is display data. It is never compared against the pantry.

`canonical_ingredient` is seeded from `fixtures/` with ~200 staples — Indian pantry basics plus
common Western ones. Without it, autocomplete is empty on day one and duplicate ingredient names
creep in immediately.

---

## LLM integration

- Suggestion is a **tool-calling loop**, not one large prompt. Tools: `get_pantry()`,
  `get_recent_meals(n)`, `get_taste_profile()`, `search_saved_recipes(query)`. No agent framework.
- The model returns which `pantry_item_id`s a recipe uses (identity only) and a `missing[]` array
  for things not owned, with quantities.
- Missing ingredients not already in `canonical_ingredient` get created there, so they can reach the
  shopping list.
- Dedup before saving: near-duplicate title plus overlapping ingredient set means show the existing
  recipe instead.
- **Failure states are real UI.** Timeout, provider error, malformed JSON after retries — all
  surface a visible, retryable error. Never an indefinite spinner. The pantry and saved recipes
  stay fully usable when the LLM is unreachable.
- **Spend guard:** monthly call counter in the DB with a hard cap. A retry loop must not be able to
  drain the balance overnight.

---

## Secrets

`.env`, never committed. `.env.example` in the repo with blank values. Required: OpenRouter API
key, session secret, model name.

---

## Testing

This is a personal app — don't build an exhaustive suite. Do test:

- The dietary deny list rejects violating responses.
- Auth: unauthenticated requests to protected routes return 404, not 401.
- Migrations apply cleanly to a populated database.

---

## Timers

Implement as target-timestamp minus now, never a `setInterval` counter. Counters die when the phone
locks, and that ruins the food.
