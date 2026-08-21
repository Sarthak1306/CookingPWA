# Handoff — start here for P5

Written at the end of the P4 session because the conversation's context window
filled up. Read this before touching anything — it covers what's actually
built (vs. what the spec says should exist), decisions already made that
shouldn't be re-litigated, real bugs already hit and fixed, and exactly what
P5 needs.

**Read `CLAUDE.md` and `docs/spec.md` first regardless** — this file assumes
you already know the hard rules (no inventory arithmetic, dietary deny list
enforced in code, nothing public, low friction, don't build ahead) and the
full data model. This file is the session-to-session diff on top of those,
not a replacement for them.

## Status: P0–P4 done, committed, all working against real data

```
0d7d193 P0: FastAPI skeleton, argon2 login, Docker/nginx/TLS deploy config, PWA shell
bc181c8 P1: Pantry CRUD with pack-size restocking and the running-low toggle
502b5bf Fix mismatched app background against sticky pantry headers
2c87a95 Real per-ingredient colors and emoji, replacing the hashed tint
8931204 Move pantry item emoji from clipped corner to right-edge center
fb208da P2: Suggest + search via LLM tool-calling loop, with exclusions
d03c7f7 P3: cook a recipe, then the "what ran out?" checklist
bccf67b P4: steps + timers + cook mode
```

30 pytest cases pass (`.venv/bin/pytest -q` from the project root). Every
phase was also verified live in an actual browser against the real
`kitchen.db` — not just automated tests. That db currently has real data:
the user's real login (`sarthak`, password unknown to any Claude session —
never ask for it, see "Auth" below), a handful of real pantry items, 11
LLM-generated recipes, and 16 real OpenRouter calls' worth of spend already
made during testing (small, a few cents each, but be aware new suggest
calls cost real money — don't spam them while testing P5).

### What each phase actually built

- **P0** — FastAPI skeleton, SQLite + numbered migrations, argon2 sessions,
  Docker/nginx/TLS deploy config, PWA shell, login screen only.
- **P1** — `canonical_ingredient` + `pantry_item`, 221-item curated fixture
  (`fixtures/canonical_ingredients.json`, regenerate via
  `fixtures/generate_fixtures.py`), real Pantry + Add/Edit screens.
- **P2** — `recipe`/`recipe_ingredient`/`recipe_step`/`taste_profile`/`job`/
  `llm_call` tables, hand-rolled OpenRouter tool-calling loop
  (`app/llm/suggest.py`), in-process async job worker (`app/jobs.py`),
  Suggest + Recipe detail screens.
- **P3** — `cook_log` + `shopping_item` tables, `POST /recipes/{id}/cook`,
  `POST /pantry/ran-out`, `POST /shopping`, the "Anything run out?" screen.
- **P4** — Cook Mode screen, target-timestamp timers, wake lock. Pure
  frontend — no backend changes.

## Established patterns — follow these, don't reinvent

- **Ask before starting a phase if there's a real fork; don't ask if there
  isn't.** Every phase this session stated scope in text first. Actual
  `AskUserQuestion` calls were reserved for genuine cross-phase ambiguity
  (e.g. P2's tools depending on P3/P5 tables, P3's shopping_item timing).
  P4 had no real fork, so it just stated scope and proceeded. Use judgment,
  don't force a question when the answer is obvious from the spec.
- **Cross-phase table dependencies get resolved by building the minimal
  table now, not stubbing forever.** P2 needed `taste_profile` and
  `cook_log`-backed `get_recent_meals` before their nominal phases — solved
  by seeding `taste_profile` with the spec's seed text in migration 0004
  (read-only until P5's write-back — **that's what P5 is**), and by
  `get_recent_meals` honestly returning `[]` until `cook_log` existed (P3),
  at which point it became a real query. Same reasoning applies if P5 needs
  something from P6.
- **Disabled-but-visible for out-of-phase UI affordances.** The design's
  bottom nav shows all 4 tabs; P1 shipped it with Suggest/Shopping/Profile
  disabled and a "Coming in a later phase" title, enabling each as its
  phase landed. Recipe detail's "Add to shopping"/"Start cooking" buttons
  got the same treatment in P2, then were enabled for real in P3/P4. If P5
  adds a Profile screen, this pattern likely applies to whatever it can't
  finish (e.g. if the taste-profile rewrite job isn't triggered yet, the
  hand-edit textarea can still be real while an auto-rewrite indicator sits
  disabled).
- **`sync_canonical_ingredients()` is an upsert-by-name on every startup,
  not a seed-once.** (`app/db.py`) Editing `fixtures/canonical_ingredients.json`
  and restarting reaches the live db automatically. Only rows matching a
  fixture name are touched — hand-added/LLM-added ingredients are never
  touched, and `pantry_item` is never touched at all. If P5 needs its own
  seed data (e.g. a default taste-profile template), consider the same
  upsert-not-seed-once shape if it's expected to be edited and re-deployed.
- **Ingredient identity resolution is centralized** in
  `app/ingredients.py` (`resolve_ingredient_id`, `pack_label`,
  `FALLBACK_COLOR`/`FALLBACK_EMOJI`) — both pantry routes and the LLM loop
  use it. Don't reimplement ingredient-name matching elsewhere.
- **Dietary deny list is checked in code, independent of any per-item
  flag** (`app/llm/deny_list.py`, keyword regex, deliberately excludes
  ambiguous terms like "sausage"/"steak"). It runs on every LLM suggestion
  result. Not relevant to P5's rewrite job unless the rewrite could somehow
  reintroduce banned words into the profile text — worth a thought, not
  necessarily worth code.
- **Frontend screen routing is a hand-rolled discriminated union** in
  `web/src/App.tsx` (`Screen` type + `setScreen`), no router library. Each
  page is a controlled component taking callbacks (`onBack`, `onFlash`,
  etc.), not doing its own navigation. A new Profile screen slots in the
  same way.
- **Real per-ingredient `color`/`emoji`** live on `canonical_ingredient`
  (migration 0003), curated by hand in `fixtures/generate_fixtures.py` —
  color always set, emoji is `""` (not a guessed generic icon) when nothing
  genuinely specific exists. This was an explicit user correction mid-P1 —
  don't reintroduce hash-based or generic-fallback icons anywhere else.

## Real bugs already hit and fixed — don't reintroduce

1. **SQLite `check_same_thread`** — FastAPI dispatches sync dependencies to
   worker threads without guaranteeing a generator dependency's setup and
   the handler that consumes it land on the same thread. Fixed by
   `sqlite3.connect(..., check_same_thread=False)` in `app/db.py`. Caused a
   real 500 on `/api/me` on reload before the fix.
2. **The app's background must be `--surface` (`#f5ead8`), not the
   design's outer `#e6dac4`.** The design's darker tone was the desktop
   backdrop *around* its phone mockup, not the phone's actual screen color.
   Using it as the real app's background made sticky headers/nav (which
   correctly use `--surface`) look like a mismatched pale stripe. Fixed by
   deleting the `--bg` token entirely — the whole app is one background
   color now (`web/src/index.css`).
3. **Never drive a timer off a decrementing `setInterval` counter** —
   CLAUDE.md forbids this explicitly (counters die when the phone locks).
   Cook Mode's timer always computes `remaining = endsAt - Date.now()`
   fresh; `setInterval` only forces re-renders. See
   `web/src/pages/CookMode.tsx`.
4. **Emoji corner positioning** — a negative CSS offset pushed the
   pantry-item emoji past the card's edge, which `overflow: hidden` then
   clipped. Positive inset + `overflow:hidden` is safe; negative offsets
   with `overflow:hidden` are not.

## Auth — don't ask for the password

The real user's password was set interactively via `scripts/create_user.py`
and was never visible to any Claude session (hidden `getpass` input). To
test as the logged-in user without it, insert a session row directly:

```python
from app.db import get_connection
from app.auth.security import new_session_token, hash_token
conn = get_connection()
user = conn.execute('SELECT id, username FROM user LIMIT 1').fetchone()
token = new_session_token()
conn.execute('INSERT INTO session (user_id, token_hash) VALUES (?, ?)', (user['id'], hash_token(token)))
conn.commit()
print(token)
```

Then `document.cookie = "session=<token>; path=/"` in the browser (via
`javascript_tool`, not the flaky `computer` click tool in this sandbox —
`computer` intermittently times out here for unknown reasons; `find`/
`form_input`/`javascript_tool` all work reliably. Use `javascript_exec` to
click buttons when `computer` hangs).

## Running it

```bash
cd "/Users/sarthak/Dev/Cooking PWA/web" && npm run build   # after any frontend change
cd "/Users/sarthak/Dev/Cooking PWA" && .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8420
```

`.env` already has a real `OPENROUTER_API_KEY` and `KITCHEN_MODEL_NAME=anthropic/claude-sonnet-5`
— loaded automatically via `python-dotenv` (`app/config.py`). Don't ask the
user for the key again, it's already there. `KITCHEN_COOKIE_SECURE` isn't
set in `.env` (defaults to `1`); that's fine for the real db over plain
HTTP locally — cookies still get sent by curl/the browser in this sandbox
regardless of the flag, only real browsers enforce Secure-over-HTTP.

If port 8420 is already bound, check `lsof -i :8420` before killing
anything — it might be the user's own terminal, not a leftover Claude
process. Ask before killing a process you didn't start.

## What's left

### P5 — taste profile write-back loop, recipe difficulty, post-cook rating (next)

The user has already answered the two open questions this doc previously
raised, and added a new feature request on top. This section is the
resulting plan — concrete enough to build from, but the exact UI copy/
layout calls are still the next session's to make. **State this scope
back to the user and confirm before writing code**, per the established
per-phase ritual — this plan hasn't been built or tested yet, unlike
everything else in this doc.

#### 1. Taste profile — structured buttons are the primary UI, not decoration

User's answer: *"I wanted it in selectable buttons instead of one big
textbox, it makes it easier for the user."* So the design's structured
pickers (effort single-select, taste multi-select chips) are the main way
to edit the profile — not just decoration next to a free-text box. This
needs a real schema change (the current `taste_profile.body_text` is a
single flat column with nowhere to put structured selections):

```sql
-- migration 0006
ALTER TABLE taste_profile ADD COLUMN effort TEXT NOT NULL DEFAULT '';
ALTER TABLE taste_profile ADD COLUMN tags_json TEXT NOT NULL DEFAULT '[]';
```

- `effort` — one of the design's four options ("Under 20 min",
  "Weeknight, 30–40 min", "An hour is fine", "All afternoon"), single-select
  buttons.
- `tags_json` — JSON array of strings (design's taste chips: "Sharp &
  lemony", "Herby", "One-pan", "Chilli heat", "Rich & creamy", "Sweet
  mains", "Slow-cooked", "Raw & cold", or whatever set feels right —
  confirm the exact list with the user, the design's list was illustrative
  mock data, not necessarily final). Storing as JSON-in-TEXT matches the
  existing `job.payload_json`/`result_json` convention in this codebase —
  don't add a separate join table for this, it's overkill for one user's
  toggle state.
- `body_text` stays for the design's "In your own words" free-text
  section — keep it, don't remove it. The button-based fields are the
  low-friction primary path; free text is still there for nuance the
  buttons can't capture.
- **What actually gets sent to the LLM**: `get_taste_profile()`
  (`app/llm/tools.py`) currently returns raw `body_text`. Change it to
  compose all three fields into one coherent text block before returning
  — something like `f"Effort: {effort}. Enjoys: {', '.join(tags)}. {body_text}"`.
  Plain string formatting, no LLM call needed for this part.
- **What the rewrite job touches**: only `body_text`. `effort` and
  `tags_json` are direct user selections via buttons — an automated job
  silently changing them would contradict "hand-editable" and would be
  confusing (a button the user didn't press changing state under them).
  The periodic rewrite only evolves the freeform prose from cook history;
  the buttons stay exactly as the user left them until they change them.

New endpoints needed: `GET /api/taste-profile` (returns `effort`, `tags`,
`body_text`, `updated_at` for the Profile screen to render) and
`PATCH /api/taste-profile` (body `{effort?, tags?, body_text?}`, updates
the single row).

#### 2. Recipe difficulty (new — wasn't in the original spec at all)

User's answer: *"I would want there to be recipes based on difficulty,
like easy, intermediate, advanced. The more I cook, I can try more complex
recipes."* This is a legitimate new feature request from the actual
project owner, not scope creep to push back on — plan it for real.

```sql
ALTER TABLE recipe ADD COLUMN difficulty TEXT NOT NULL DEFAULT 'intermediate';
```

- The LLM assigns this per recipe. Add `"difficulty": "easy" | "intermediate" | "advanced"`
  to the JSON schema in `SYSTEM_PROMPT` (`app/llm/suggest.py`) and store it
  in `_save_new_recipe`.
- Display: a badge on Suggest result cards (`RecipeSummary` type +
  `_recipe_summary()` in `app/routes/suggest.py` need the field) and on
  Recipe detail near the existing meta line (time · servings).
- **Open call, confirm with the user rather than assuming either way**:
  "the more I cook, I can try more complex recipes" could mean (a) just
  show the label and let the user self-select what to attempt — no app
  logic needed beyond display, matches "low friction" and doesn't
  over-build, or (b) the suggest loop should actually bias toward easier
  recipes early and loosen up as `cook_log` grows (e.g. pass a cook-count-
  derived hint into the system prompt or taste profile text). (a) is the
  safe default if the conversation doesn't clarify — it's much less code
  and nothing about it forecloses adding (b) later. Don't build (b)
  without confirming that's actually wanted; it's meaningfully more work
  (suggest-loop context changes, not just a schema + badge) for a
  behavior the user described as their own judgment call, not necessarily
  something they're asking the app to automate.

#### 3. Post-cook rating (resolves last session's open question #1)

User's answer: *"I would want there to be a rating I can give to a recipe
after cooking, based on which I can be recommended or not recommended
certain things."* So yes, capture it — `cook_log.rating` already exists
in the schema and has sat unused since P3.

- **Where**: the leanest placement is folding a rating prompt into the
  top of the existing "Anything run out?" screen (`RanOut.tsx`) rather
  than inserting a whole new screen between Cook Mode and it — one less
  screen transition, matches the spec's own "skippable in one tap" spirit
  for that screen. This is a UI call, not a hard requirement — confirm
  with the user if unsure, but it's the reasonable default.
- **Plumbing gap to close**: `POST /recipes/{id}/cook` already returns
  `cook_log_id` in its response (`app/routes/suggest.py`), but the
  frontend currently discards it — `CookMode.tsx`'s `onFinished` callback
  and `App.tsx`'s `'ranOut'` screen state only carry `usedItems`, not the
  cook_log id. That needs threading through so the rating can be attached
  to the right row.
- **Scale**: design has no rating widget to copy (wasn't in original
  scope). A simple 1–5 tap-once row is a reasonable default — flexible
  enough for the rewrite job to weight recipes later. Confirm with the
  user if a coarser thumbs-up/meh/thumbs-down feels lower-friction to
  them; either is a small change.
- New endpoint: `POST /api/cook-log/{id}/rate`, body `{rating: int}`.
- **How rating actually influences future suggestions** — two
  complementary mechanisms, both worth doing, neither is a separate
  "recommendation engine" (that would be over-building):
  1. `get_recent_meals()` (`app/llm/tools.py`) should include `rating`
     alongside `title`/`cuisine`/`cooked_at` in what it returns, so the
     model sees recent ratings directly during a suggest call.
  2. The taste-profile rewrite job (§1 above) is explicitly specified in
     `docs/spec.md` to rewrite `body_text` "from ratings and history" —
     that's the mechanism for ratings to shape the standing profile over
     time, not a bolt-on. This is also why per-ingredient sentiment
     tracking or a dedicated recommendation table isn't needed: the
     existing prose-rewrite loop is designed to absorb exactly this kind
     of pattern ("keeps rating spicy dishes low") into plain text the
     model already reads every time.

#### Tying it together

The rewrite job itself (dispatched every ~10 `cook_log` rows, per spec) is
still the right shape from the previous version of this doc: a `job` kind
(e.g. `"rewrite_profile"`), reusing `app/jobs.py` / `app/llm/spend_guard.py`
rather than new plumbing, ideally on a cheap model — no cheap-model config
exists yet (only `KITCHEN_MODEL_NAME` for the main suggestion loop), so
add a second config var (e.g. `KITCHEN_MODEL_NAME_CHEAP`) the same way
`KITCHEN_MONTHLY_CALL_CAP` was added in P2. The rewrite prompt's input is
now concretely: the last ~10 `cook_log` rows (title, cuisine, rating,
cooked_at via a join) plus the current `body_text`, output is a replacement
`body_text` — leave `effort`/`tags_json` untouched as established above.

Frontend: new Profile screen (design has the layout — effort buttons,
taste chip grid, free-text area, save), enabling the currently-disabled
Profile bottom-nav tab per the established pattern. Recipe cards/detail
gain a difficulty badge. RanOut screen gains a rating row at the top.

### P6 — shopping list screen

`shopping_item` already exists and is being written to (P3's ran-out flow,
Recipe detail's missing-ingredient "Add" buttons). What's missing is the
screen itself: list all outstanding `shopping_item` rows, manual free-text
add, and tick-off — which per the schema comment in migration 0005 means
**deleting the row and writing/updating a `pantry_item` at pack size**, not
flipping a status flag (there is no ticked column by design). Enabling the
Shopping bottom-nav tab is the other half.

### P7–P9 (optional, spec says "only if wanted" — confirm before starting)

YouTube import (captions/description only), MCP server over the pantry db,
barcode scan. Don't start these without the user explicitly asking — they're
explicitly marked optional/later in `docs/spec.md`.

## Don't re-litigate

These were explicit user decisions this session — take them as settled,
don't ask again:

- Bottom nav always shows all 4 tabs; disable + "Coming in a later phase"
  title for whatever isn't built yet, rather than hiding tabs.
- Out-of-phase buttons (Start cooking, Add to shopping, etc.) render
  visibly-disabled rather than being omitted, matching the design.
- Per-ingredient emoji is single, positioned at vertical-center of the
  right edge (not tiled as a background pattern, not in the corner) —
  color always set, emoji omitted (not a generic fallback icon) when
  nothing specific exists.
- App background is one flat color (`--surface`) throughout, no two-tone
  page/card distinction from the design's desktop mockup framing.
