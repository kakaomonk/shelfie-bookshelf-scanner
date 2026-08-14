# Shelfie — Bookshelf → Library Inventory

Turn a photo of a bookshelf into a structured personal library: an Expo app takes the photo, a
Django API finds individual book spines locally, reads title/author off them with a hosted
vision-language model, matches each read against a catalog of canonical books, and asks a human
to confirm anything it isn't confident about.

Take-home task for a Full Stack Developer (AI & Computer Vision) role. See `AI_USAGE.md` for how
AI tools were used to build it.

## Project layout

- `backend/` — Django + Django REST Framework API (Python 3.12, CPU-only local model, Claude for
  reading spines, SQLite for storage).
- `frontend/` — Expo (React Native + TypeScript) mobile app.
- `catalog.csv` — the canonical book catalog matched against (`scripts/generate_catalog.py` built it).
- `test_photos/` — real bookshelf photos used during development.
- `scripts/measure_pipeline.py` — measures real per-photo latency/cost (numbers below came from it).

## Setup

Requires Python 3.10–3.12 (tested with 3.12; on Apple Silicon use a native arm64 interpreter --
Rosetta/x86_64 Python caps out on an old `torch` build and is noticeably slower) and Node 18+.

### Backend

```bash
cd backend
python3.12 -m venv venv
venv/bin/pip install -r requirements.txt

cp .env.example .env
# edit .env and set ANTHROPIC_API_KEY (your own key, or a company-issued spend-capped one --
# either works, per the brief)

venv/bin/python manage.py migrate
venv/bin/python manage.py load_catalog     # loads catalog.csv into SQLite
venv/bin/python manage.py runserver 0.0.0.0:8000   # 0.0.0.0, not 127.0.0.1, so a phone on the same Wi-Fi can reach it
```

Run the tests with `venv/bin/python manage.py test scanner`.

### Frontend

Needs Node 18+ (Expo SDK 57 requires it; check with `node --version` -- if it's older, install a
current LTS with [nvm](https://github.com/nvm-sh/nvm) rather than fighting the system Node).

```bash
cd frontend
npm install

cp .env.example .env
# edit .env: EXPO_PUBLIC_API_URL=http://<your-machine's-LAN-IP>:8000
# find your LAN IP on macOS with: ipconfig getifaddr en0

npx expo start
```

Scan the QR code with Expo Go on a phone on the same Wi-Fi network, or press `i`/`a` for a
simulator (simulators can usually also reach `localhost` directly, but the LAN IP works either way).

## Architecture

```mermaid
%%{init: {"themeVariables": {"fontSize": "20px"}, "flowchart": {"nodeSpacing": 45, "rankSpacing": 65}}}%%
flowchart TD
    A["Take / pick a photo<br/>Expo app"]:::client
    B["POST /api/scan<br/>Django"]:::backend
    C["FastSAM<br/>segment individual spines<br/>local · CPU · off-the-shelf"]:::local
    D["Claude Haiku<br/>1 batched call reads every crop<br/>hosted · Anthropic API"]:::hosted
    E["rapidfuzz matching<br/>vs catalog.csv, 114 entries"]:::backend
    F{"confidence"}:::backend
    G["POST /api/library<br/>auto-add or confirm"]:::backend
    Rv["Review screen<br/>confirm · edit · discard<br/>Expo app"]:::client
    X["not persisted"]:::muted
    DB[("SQLite<br/>LibraryEntry")]:::backend
    L["Library list<br/>Expo app"]:::client

    A -->|multipart photo| B --> C -->|spine crops| D -->|title / author per spine| E --> F
    F -->|high confidence| G
    F -->|low confidence / unmatched| Rv
    Rv -->|confirm| G
    Rv -->|discard| X
    G --> DB --> L

    classDef client fill:#dde4ec,stroke:#274060,color:#1b1f1a,stroke-width:2px
    classDef backend fill:#f1e3cd,stroke:#a06a1e,color:#1b1f1a,stroke-width:2px
    classDef local fill:#dcece2,stroke:#34694b,color:#1b1f1a,stroke-width:2px
    classDef hosted fill:#f2ddda,stroke:#9c3b34,color:#1b1f1a,stroke-width:2px
    classDef muted fill:#eeeeee,stroke:#999999,color:#555555
```

Color marks where each step actually runs -- blue is the Expo app, tan is Django, **green is the
one local/CPU step, red is the one hosted API call**. Geometry stays on the machine; reading text is
the only step that leaves it. Nothing reaches `LibraryEntry` (bottom) without either clearing the
confidence bar or a human tapping Confirm.

**Local vs. hosted, and why**: FastSAM (Ultralytics, off-the-shelf pretrained weights, no
training/fine-tuning) runs locally on CPU and does pure geometry -- finding *where* spines are.
It's class-agnostic segmentation rather than a COCO-pretrained detector's single `book` class,
because COCO's `book` annotations are mostly isolated books/stacks; on a packed shelf that class
tends to draw one or two boxes around the whole thing, not one per spine. FastSAM segments by
color/texture boundary instead, which is what actually separates adjacent spines, and it's free
and instant since it never leaves the machine. *Reading* the text needs real language+vision
understanding (angled, stylized, partly occluded text) -- that's what the hosted model, Claude
Haiku, is for. Every spine crop from one photo goes into a **single** Claude call (multiple images,
one message) instead of one call per spine, because a shelf can hold 20-30 books and that's the
difference between 1 round trip and 20-30 for both latency and cost.

**Matching**: title similarity via `token_sort_ratio` (order-independent) against the title and
every `alt_titles` entry, scaled down by a length-ratio penalty -- otherwise a short read like
"Foundation" scores as a near-perfect match against "Foundation and Empire" purely because it's a
literal substring, which is exactly the failure mode the catalog is built to expose. Author
similarity normalizes "Lastname, Firstname" order and weights last-name similarity over the full
string, since first names legitimately vary in form (initials vs. spelled out) for a correct
match. A missing author read isn't scored as a mismatch, just a small penalty for the missing
corroboration. Full rationale and the tie-breaking rule are documented in
`backend/scanner/matching.py`'s module docstring, next to the code they explain.

**Human in the loop**: high-confidence matches auto-add (the brief allows this explicitly), but
still render in the app as "added automatically" rather than vanishing silently. Everything else
-- low-confidence matches, ambiguous ties, unmatched reads, and spines the VLM couldn't read at
all -- goes to a review card with the best guess pre-filled, tappable alternative candidates for
ties, and explicit Confirm/Discard actions. Nothing is written to the database as a
`LibraryEntry` until a person acts on it; there's no separate "pending" table.

**Graceful failure**: every stage is designed to degrade instead of crash. A corrupt upload
returns 400 with a message. Zero spines detected returns 200 with an empty list and a warning,
not an error. A local-model exception, a VLM timeout/auth failure, or a malformed VLM response
all turn into per-book `legible: false` plus a `warnings` entry, never a 500. If the confirm call
for an auto-added high-confidence match itself fails, that book falls back to rendering as a
normal manual-review card instead of silently disappearing. See `backend/scanner/views.py` and
`backend/scanner/vlm.py`.

## Screenshots

_Pending a real device test with a live API key -- no iOS Simulator/Android emulator was available
in the environment this was built in to generate these from a mobile browser/renderer, and a
web-rendered React Native screenshot wouldn't represent the real app anyway. Will be added here
(scan screen, review queue, library list) before submission._

## Measured latency & cost

Measured with `scripts/measure_pipeline.py` against `test_photos/shelf_1.jpg` (a real,
cluttered shelf photo, 3024×4032, 22 detected spine candidates) on an Apple Silicon Mac, CPU only.

| Stage | Time | Notes |
|---|---|---|
| Spine detection (cold, incl. model load) | ~6.0s | Once per backend process |
| Spine detection (warm) | ~2.4-4.3s | Every scan after the first in a given process; varies with system load |
| VLM read (Claude Haiku, 22 crops, 1 batched call) | ~8.5-10.6s | One network round trip regardless of spine count (up to the 30-crop cap) |
| Tokens per photo | ~12,900 in / ~800-820 out | 22 images + prompt in, one structured tool-call out |
| Est. cost per photo | **~$0.017** | `12,900/1e6 * $1.00 + 810/1e6 * $5.00`, Haiku 4.5's published per-token rate |

The VLM call was measured through OpenRouter's Anthropic-compatible passthrough (`ANTHROPIC_BASE_URL`,
see `.env.example`) rather than `api.anthropic.com` directly -- a direct Anthropic key wasn't
available yet at measurement time. The dollar figure above applies Anthropic's own published Haiku
rate to the actual token counts OpenRouter reported, so it's the real expected cost on the direct
path the README otherwise describes, not an OpenRouter-specific number; latency against
`api.anthropic.com` directly would likely be a little lower (one less network hop).

On this real photo (not a clean staged shot -- a shelf with a massage-gun box and several
non-catalog books mixed in), the VLM legibly read 7 of 22 candidates; the other 15 were correctly
recognized as untrustworthy or off (see "Known limitations" -- most were furniture, not spines).
All 7 legible reads correctly landed as `unmatched` rather than false-matching to something in the
114-book catalog (none of these specific books are in it) -- exactly the outcome that should
happen: the matcher didn't force a confident-looking wrong answer just because *something* scored
highest.

A second round of real-device testing (an actual bookshelf, plus a shelf of board games as a
stress case) confirmed the pattern: FastSAM doesn't know what a book is, so a board game box or
a product box gets detected exactly like a spine would. But it turns out that's fine end to end --
the VLM doesn't know what a book is either, and faithfully reads whatever text is actually printed
on the box (a board game's title, a product name), which is the correct behavior for a model whose
job is "read the text in this crop," not "judge whether this is a book." Since board games and
products aren't in the catalog, these reads land as `unmatched` and get discarded in one tap, same
as the massage gun above. The one real bug this round of testing did surface -- illegible spines
all resolving to a fake "Dune" suggestion -- was a matching-logic bug, not a detection/VLM problem;
see `backend/scanner/matching.py`'s `test_unmatched_never_suggests_a_fake_best_match` for the fix.

The VLM row is the one number this README can't honestly fill in yet: a working `ANTHROPIC_API_KEY`
wasn't available at the time of the last update. `scripts/measure_pipeline.py` already computes
and prints exactly these numbers (elapsed time, input/output tokens, estimated cost) the moment a
key is in place -- `cd backend && venv/bin/python ../scripts/measure_pipeline.py ../test_photos/shelf_1.jpg`.
This is a documented gap, not a guessed number standing in for one.

Detection latency is the more interesting local-vs-hosted number regardless: at ~4-7s on CPU for
a single photo, it's well within "wait for it while looking at your phone" territory, and it's
free per-request since the model is loaded once per process, not per photo.

## The catalog

`catalog.csv` has 114 entries (see `scripts/generate_catalog.py` for exactly how it was built --
a hand-curated list run through a small script rather than typed as raw CSV, mainly so publisher
names containing commas escape correctly). It's deliberately messy, on purpose, in the specific
ways the brief calls out:

- **Two editions of the same book as separate rows**: `Dune` (1965 Chilton / 2019 Ace),
  `1984`, `The Hobbit`.
- **The same book under two different titles, as separate rows** (no `alt_titles` crutch):
  `Harry Potter and the Philosopher's Stone` / `...Sorcerer's Stone` -- these differ by exactly
  one word, which is a real stress test for the title matcher.
- **The same book under two titles, via `alt_titles` instead**: `The Golden Compass` /
  `Northern Lights`, showing the other way this problem gets solved in practice.
- **Two genuinely different books sharing an exact title**: `Foundation` (Isaac Asimov) vs.
  `Foundation` (Peter Ackroyd, a history book) -- without an author read, these are truly
  ambiguous and the matcher is expected to say so, not guess.
- **An omnibus alongside its individual volumes**: `The Lord of the Rings` next to `The
  Fellowship of the Ring` / `The Two Towers` / `The Return of the King`; same pattern for Narnia.
- **Title substrings**: the Foundation trilogy (`Foundation` / `Foundation and Empire` / `Second
  Foundation`, same author, escalating substring risk), plus `It` vs. `It Ends with Us`.
- **Author names in more than one form**: initials (`J.K. Rowling`) vs. spelled out (used in a
  test as if a VLM read it that way), "Lastname, Firstname" order (`Dostoyevsky, Fyodor M.`,
  `Tolstoy, Leo`, `García Márquez, Gabriel`), and accented vs. unaccented spelling of the same name
  across two different entries.
- Bonus, not required by the brief: `The Cuckoo's Calling` is credited to "Robert Galbraith" --
  J.K. Rowling's crime-fiction pseudonym -- deliberately *not* cross-referenced, since a shelf
  photo gives no way to know they're the same person.

It's weighted toward books people plausibly own (bestsellers, classics, popular YA/nonfiction)
rather than obscure titles, since the presentation runs against the interviewers' own shelves.
Publishers/years are approximate, not fact-checked line by line -- the deliberate ambiguity is the
point, bibliographic precision isn't.

## Key decisions & tradeoffs

- **FastSAM over a COCO-pretrained detector** for the reason above (class-agnostic segmentation
  actually separates adjacent spines; a `book`-class detector tends not to). Tradeoff: FastSAM has
  no concept of "book" at all, so it also proposes non-book regions (see "What's unfinished").
- **One VLM call per photo, not one per spine** -- the single biggest lever on cost and latency,
  at the cost of a hard cap (30 spines per call; overflow is dropped with a surfaced warning
  rather than silently, but isn't chunked into a follow-up call yet).
- **Claude Haiku, not a larger model** -- reading printed text off a crop is a perception task,
  not one that benefits from a bigger reasoning model; Haiku is the cheaper, faster fit.
- **Forced tool-use instead of freeform JSON** from the VLM, so malformed JSON is a rare edge case
  instead of the common one -- but the parse is still wrapped defensively on top of that, since
  "rare" isn't "never."
- **No separate "pending review" model or table.** Scan candidates live only in the `/api/scan`
  response and the Expo app's in-memory state while under review. Simpler, and it means a
  `LibraryEntry` is always something a person actually looked at -- but it also means a scan's
  candidates don't survive an app restart mid-review; there's nothing to resume from.
- **Editing a review card clears its catalog link** rather than re-running the matcher against the
  corrected text. Simple and predictable, at the cost of not catching "the user's correction
  actually matches a different catalog entry."
- **No navigation library, no state-management library.** Two always-visible screens (Scan,
  Library) switching on local `useState` cover the whole app. Fine at this scope; would need
  revisiting if the app grew more screens or deep-linking.
- **SQLite, no auth, no deployment** -- exactly what the brief says isn't graded, so no time went
  there.

## What's unfinished

- **Detection false-positives on anything tall and narrow, not just books.** FastSAM has no
  concept of "book" -- an open drawer gap, a shelf divider, a board game box, or a product box all
  get detected exactly like a spine would, confirmed on two different real shelves (one with
  furniture gaps, one with board games). Threshold tuning against a real photo
  (`test_photos/shelf_1.jpg`) cut the most obvious cases, but didn't eliminate the problem. And the
  VLM doesn't second-guess it either -- it faithfully reads whatever text is actually printed on a
  non-book box, which is correct given its job is "read the text in this crop," not "judge whether
  this is a book." Since none of that shows up in the catalog, it lands as `unmatched` and gets
  discarded in one tap -- it degrades the review experience (more items to dismiss), not the data
  quality (nothing wrong ever reaches the library). With more time, a cheap next step would be
  constraining candidates to a detected shelf-surface band instead of the whole frame.
- **VLM numbers were measured through an OpenRouter passthrough, not `api.anthropic.com`
  directly** (see "Measured latency & cost" above) -- a direct Anthropic key wasn't available yet
  when this was measured. Same model, same token accounting, likely marginally lower latency on
  the direct path; will re-measure directly if a key arrives before submission.
- **No re-matching after a manual correction** in the review screen, as noted above.
- **The 30-spines-per-call cap isn't chunked into follow-up calls** for denser shelves -- it's
  surfaced as a warning instead, which is honest but not a full solution.
- **HEIC photos aren't decoded server-side** (Pillow doesn't support HEIC without an extra
  dependency that wasn't worth adding) -- not an issue through the app itself, since Expo's image
  picker re-encodes to JPEG before upload; only matters for a photo supplied directly as a file.
- With another day: chunk the VLM call for larger shelves, constrain detection to a shelf-surface
  region, and re-run the matcher after manual edits in the review screen.
