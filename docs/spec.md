# Kitchen — personal cooking assistant

Single-user pantry tracker + recipe suggester. Self-hosted on my own VPS behind nginx at
`kitchen.sarthaksrivastava.tech`. Not a public product.

---

## Constraints

- One user (me), behind a plain username + password login. Not open to the internet.
- Online-only. PWA for home-screen install and fullscreen, no offline sync layer.
- Cheap to run. LLM via OpenRouter, one topped-up balance, model chosen by config string.
- Runs alongside the existing nginx-served portfolio on the same box. Portfolio config untouched.
- Low friction beats accuracy. If maintaining it feels like data entry, I'll stop using it.

## Auth

- One `user` row, argon2 password hash. Password set by CLI script — **no signup endpoint**.
- `POST /login` verifies, creates a `session` row, sets cookie: `HttpOnly; Secure; SameSite=Lax`,
  one year expiry. Log in once per device, then never again.
- Sessions in a table, not a signed JWT — deleting a row revokes a device.
- Failed-attempt lockout on `/login`. Bots will find the subdomain within days of the cert issuing.
- Extra users are created by hand if I ever want to give someone access.

## Dietary rules

**Absolute — enforced in code, not just prompt:** never seafood, beef, or pork.
Every ingredient in a model response is checked against a deny list. A hit rejects the whole
response and regenerates with the violation named.

**Preference, not restriction:** leans Indian — curries, rice, dal, paneer. Also Mexican-style
wraps, sandwiches. Main proteins chicken, paneer, eggs. Open to anything that looks good;
the model should suggest outside these cuisines when it's worth it.

**Effort:** up to an hour is fine. Batch cooking and meal prep actively wanted.

---

## Stack

| Layer | Choice | Note |
|---|---|---|
| Backend | FastAPI (Python) | single process |
| DB | SQLite | one file, nightly cron backup off-box |
| Frontend | Vite + React, `vite-plugin-pwa` | built to `dist/`, served static by FastAPI |
| LLM | OpenRouter | model as config string, swappable |
| Jobs | SQLite `job` table + one asyncio worker | no Redis, no Celery |
| Deploy | Docker Compose, bound to `127.0.0.1:8420` | nginx reverse-proxies the subdomain |
| TLS | certbot via nginx plugin | required — PWAs need HTTPS |

---

## Data model

```
user                 : id, username, password_hash, created_at
session              : id, user_id, token_hash, created_at, last_seen_at

canonical_ingredient : id, name, default_unit, category, deny_flag,
                       common_purchase_qty, common_purchase_unit
pantry_item          : id, ingredient_id, qty_label, is_low, updated_at

recipe               : id, title, base_servings, source(llm|manual|youtube),
                       cuisine, est_minutes, keeps_well, created_at
recipe_ingredient    : recipe_id, ingredient_id, qty, unit, optional_flag
recipe_step          : id, recipe_id, position, text, timer_seconds NULL, video_start_s NULL

cook_log             : id, recipe_id, cooked_at, rating, notes
shopping_item        : id, ingredient_id, added_at, added_from(ran_out|manual|recipe)
taste_profile        : id, body_text, updated_at
job                  : id, kind, payload_json, status, result_json, error
```

**`canonical_ingredient`** stops "tomato" / "tomatoes" / "Tomato" becoming three rows.

**`qty_label` is free text, and the app never does maths on it.** I write "500g bag" or "half
full" for my own benefit. Nothing subtracts from it. See the section below.

**`is_low` is a manual toggle**, not a computed threshold — a threshold needs numbers to compare
against, and there are no reliable numbers here. I flip it when I notice.

**`common_purchase_qty`** is the friction fix. I shop in packs, not grams — potatoes are a 500g
bag, eggs are a dozen. Restocking is `+1 bag`, not typing a number and picking a unit. Learned
from my own history, not shipped as a guess.

**`recipe_ingredient` keeps qty and unit** — I need to *read* "2 tbsp oil" while cooking. It's
only pantry matching that's quantity-free.

**`base_servings`** — recipes scale for display when I want more portions. Nothing else depends
on it.

**`keeps_well`** lets batch-flavoured requests favour reheat-friendly recipes.

---

## The app does not do arithmetic

This is the central design decision. The pantry tracks **what I have**, not **how much is left**.

Strict accounting drifts. Deduct 300g of potatoes when I actually used four, and two weeks later
the numbers are fiction — and an app confidently wrong about my pantry is worse than a vague one.
More to the point: I don't measure to the gram, so the input was never accurate to begin with.

So:

- Recipes match the pantry on **ingredient identity only**. Do I have oil, yes or no.
- After cooking, the app shows **only the ingredients that recipe used** and asks which ran out.
  Tap them → they leave the pantry and land on the shopping list. That's the whole update flow.
- No deduction, no unit conversion, no confirm-the-numbers screen.
- `is_low` is my own toggle. The suggester either builds around using that item up, or avoids it.
- No cooked-food or leftovers tracking. If it's in the fridge, I'll eat it if I want to.

**Known cost, accepted:** the app can't tell I'm down to my last 100g of chicken, so it may suggest
something needing more. The `is_low` flag is the mitigation, and it's good enough.

---

## LLM design

### Suggestion is a tool-calling loop, not one big prompt

Tools exposed to the model:

- `get_pantry()`
- `get_recent_meals(n)`
- `get_taste_profile()`
- `search_saved_recipes(query)`

The model decides what to pull. "Something quick with chicken" and "what can I batch for the
week?" need different context. ~150 lines of loop, no agent framework.

*(`get_expiring_soon` dropped — I don't track expiry.)*

### Ingredient IDs, not free text

Pantry goes to the model as structured items with IDs and names. It returns which
`pantry_item_id`s each recipe uses — identity only, no quantities. Ingredients I don't own go in a
separate `missing[]` array with the quantity the recipe calls for, since that quantity is worth
displaying and worth putting on the shopping list.

The IDs are what stop "2 medium onions" and my `onions` pantry row being treated as different
things.

### Exclusions — two separate things

- **Out of stock**: one-tap from the suggest screen, writes to the pantry, persists.
  For when I'm at the counter and the onions are gone.
- **Avoid for this request only**: a chip on the suggest screen, doesn't touch the pantry.
  For when I *have* onions and just don't feel like chopping them.

Both feed one `exclude[]` param. Enforced in code too — saved recipes containing the ingredient are
filtered out before the model sees them.

### Missing ingredients close the loop

Anything in `missing[]` that isn't already a canonical ingredient gets created as one on the spot,
so it can go straight onto the shopping list. Recipe needs it → buy it → tick it off → it's in the
pantry. If that chain breaks anywhere, the app stops being useful.

### Unit conversion — mostly deleted, not solved

Since nothing is subtracted from the pantry, "2 tbsp oil" against "oil: 1L bottle" never has to be
reconciled. The model answers "does he have oil?" — that's it. Recipe quantities are for reading,
not matching.

The model still returns which `pantry_item_id`s a recipe uses, so the post-cook "what ran out?"
checklist shows only relevant items. Identity mapping, no arithmetic.

### Recipe dedup

Before saving a generated recipe, check for a near-duplicate title and overlapping ingredient set.
On a hit, surface the existing recipe instead of saving a sixth variation of the same dal.

### Failure states

OpenRouter down, request timed out, malformed JSON after retries — all surface a visible error with
a retry button. Never an indefinite spinner. Cached recipes and the whole pantry stay usable when
the LLM is unreachable; only suggestion is degraded.

### Taste profile is plain text, not embeddings

~200 words injected into every suggestion prompt. After every ~10 cook logs, a background call
rewrites it from ratings and history. Hand-editable, which a vector store isn't.

**Seed text:**

> Leans towards Indian food — curries, rice dishes, dal, paneer — and also makes Mexican-style
> wraps and sandwiches. Main proteins are chicken, paneer, and eggs. This is a preference, not a
> restriction: suggest recipes from any cuisine when they're genuinely good, and don't hesitate to
> introduce something new. The one hard rule is no seafood, no beef, no pork, ever. Happy to spend
> up to an hour cooking and open to batch recipes that hold for a few days. Assume a normal home
> kitchen with no specialist equipment. The pantry records what he has, not how much — assume a
> usable amount of anything listed unless it's flagged as running low.

### Cost control

- Nothing calls the LLM on app open. Only explicit "suggest" or "search" does.
- Every generated recipe is saved permanently. The library compounds; generation frequency drops.
- Cheap model for extraction and profile rewrites, better model for suggestions.

---

## Screens

1. **Login** — username, password. Seen once per device.
2. **Pantry** — grouped by category, `is_low` flag visible, `+1 pack` quick restock, tap to edit label
3. **Add item** — name autocompletes against canonical list, quantity label defaults to usual pack size
4. **Suggest & search** — free-text box, `avoid:` chips, results as cards with have/missing
5. **Recipe detail** — ingredients marked have/missing, servings scaler, cook button
6. **Cook mode** — one step at a time, per-step timers, wake lock on, big text
7. **What ran out?** — after cooking, only the ingredients that recipe used, tap the ones that
   finished. They leave the pantry and land on the shopping list. Skippable in one tap.
8. **Shopping list** — auto-filled from ran-out and missing ingredients, tickable, adds back at pack size
9. **Profile** — read and hand-edit the taste profile

**Mobile first.** Phone, often with messy hands. Big tap targets, minimal typing, no dense tables.

**Timers:** target-timestamp minus now, never a `setInterval` counter — counters die on screen lock.

---

## Build order

| Phase | Deliverable |
|---|---|
| P0 | FastAPI + Docker + nginx subdomain + TLS + login. PWA installs on phone. Nothing else works yet — but deploy is never the scary unknown later. |
| P1 | Pantry CRUD with pack-size restocking. Useful on its own. |
| P2 | Suggest + search via tool-calling loop, with exclusions. |
| P3 | Cook a recipe, then the "what ran out?" checklist. |
| P4 | Steps + timers + cook mode. |
| P5 | Taste profile write-back loop. |
| P6 | Shopping list proper — manual adds, tick-off back into pantry. |

Optional, later, only if wanted:

- P7 — YouTube import, **captions and description only**. No Whisper, no vision.
- P8 — MCP server over the pantry DB, so Claude Code can query the kitchen directly.
- P9 — Barcode scan via phone camera + Open Food Facts.

---

## Deploy notes

- App binds `127.0.0.1:8420`. Never `0.0.0.0` — that bypasses nginx and TLS.
- nginx: new server block on `kitchen.sarthaksrivastava.tech`, `proxy_pass` to 8420,
  then `certbot --nginx -d kitchen.sarthaksrivastava.tech`.
- DNS A record must resolve before certbot will issue.
- fail2ban or a rate limit on `/login`.
- SQLite file on a mounted volume, not inside the container.
- Nightly cron copy of the DB off-box. It's one file; there's no excuse — and restore it once to
  confirm the backup actually works. An untested backup isn't a backup.
- `restart: unless-stopped` in compose, plus a `/healthz` endpoint.

## Migrations

Decided at P0, before there's data worth keeping. The schema changes six or seven times across the
phases, and by P3 there's real pantry data in there. Alembic, or hand-rolled numbered SQL files —
either works, but not "drop and recreate."

## Seed data

`canonical_ingredient` ships with ~200 staples as a fixture — Indian pantry basics plus common
Western ones. Autocomplete against an empty table on day one is a bad first impression, and it's
how the "tomato / tomatoes / Tomato" problem sneaks back in.

## Secrets and spend

- OpenRouter key in `.env`, never committed. `.env.example` in the repo with blank values.
- Monthly call counter in the DB with a hard cap. A retry loop shouldn't be able to quietly drain
  the balance while I'm asleep.
- OpenRouter's own spend limit set as a second line of defence.
