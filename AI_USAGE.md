# AI Usage

This project was built with heavy use of AI coding tools, as the task brief explicitly invites
("assume you will be asked to justify any line in the repository" is taken seriously below).

## Tools

- **Claude Code (Opus 5)** — used throughout, interactively, turn by turn, for essentially every
  file in this repository: architecture decisions, scaffolding, implementation, tests, and this
  documentation. Not a single unattended generation — every non-trivial decision (model choice,
  matching algorithm, thresholds, what to cut) was proposed by the assistant and approved,
  redirected, or overridden by the author in the same conversation.
- **Anthropic Claude API (`claude-haiku-4-5`), vision** — not a coding tool. This is a runtime
  dependency of the app itself: the hosted vision-language model that reads title/author text off
  spine crops. See the Architecture section of the README for why this model and this call shape.

## How the work actually happened

The author drove the session conversationally: stated the task (from the brief PDF), answered
clarifying questions (VLM provider choice, deadline, that real test photos would be supplied),
and then reviewed/approved each subsequent step rather than writing files directly. Concretely:

- **Proposed by the assistant, accepted as-is**: the overall pipeline shape (local detection →
  batched VLM read → fuzzy match → human review), the Django/DRF and Expo scaffolding, the
  matching algorithm's scoring formula, the catalog's messiness categories, the tool-use-forced
  VLM call, and most of the error-handling paths.
- **Proposed by the assistant, corrected after real data**: the spine-detection confidence/aspect
  ratio/area thresholds were initially tuned only against a synthetic test image. Once the author
  supplied a real bookshelf photo (`test_photos/shelf_1.jpg`), it surfaced false positives
  (furniture, shelf dividers) the synthetic test never would have -- the thresholds were retuned
  against that real photo, and the residual limitation was written up honestly rather than
  hidden (see README "What's unfinished"). Similarly, the frontend was originally scaffolded on
  Expo SDK 57; it passed every local check (typecheck, bundle export) but failed to open in the
  store-distributed Expo Go app on the author's actual phone, since that app only supports SDK 54
  as of this writing. Downgraded once that real-device failure surfaced it -- a category of
  problem no amount of local tooling would have caught.
- **Human judgment calls**: which hosted VLM provider to use and whose API key to spend (the
  author's own), when to stop iterating and ship a given piece, and reviewing every diff before
  it was committed.
- **The catalog** (`catalog.csv`, 114 entries): drafted by Claude Code as a curated list encoding
  the specific messiness the brief asks for (duplicate editions, US/UK titles, shared titles,
  omnibus/volumes, substrings, author-name-format variance), generated via
  `scripts/generate_catalog.py` rather than hand-typed CSV, specifically to get correct escaping
  on the several publisher names that contain commas. Not independently fact-checked entry by
  entry (dates/publishers are approximate) -- the messiness is deliberate, the bibliographic
  precision is not the point.
- **Real-device testing found real bugs code review didn't.** Once the author had the app running
  on their own phone against their own bookshelves, three genuine bugs surfaced that no amount of
  synthetic testing had caught: illegible spine reads were silently suggesting a fake "Dune" match
  (a stable-sort artifact in `matching.py` -- an all-zero score tie defaulted to the lowest catalog
  id), spines showing only a book's main title (no subtitle) were scoring as unmatched even with a
  correct read, and choosing a photo from the iOS photo library (HEIC format) failed to decode
  server-side entirely. All three were diagnosed and fixed in the same session, each with a
  regression test or an explicit before/after verification against the real photo/device that
  found it -- see the commit history for `matching.py` and `scanner/views.py` around this period.
  This is the part of the process most worth being honest about: the assistant's own synthetic
  tests and code review gave false confidence here, and it took the author actually using the app
  to surface what was really broken.
- **An investigated-and-rejected fix.** A real limitation (detection performing worse on
  tilted/leaning spines) had an "obvious" fix -- score FastSAM's oriented mask polygon instead of
  its axis-aligned box. The assistant tested this against the real test photo before proposing it,
  found it would trade one failure mode (missed tilted books) for a worse one (more non-book
  diagonal noise passing the filter), and reported that back rather than implementing it or
  quietly dropping the idea. Documented as a known limitation with the actual reasoning, not just
  "not done."

## What AI did not do

- Did not fine-tune or train any model -- the brief explicitly forbids it, and no attempt was
  made to work around that.
- Did not pick the hosted VLM provider or spend real API budget without the author's explicit
  say-so.
- Did not fabricate the latency/cost numbers in the README -- they come from
  `scripts/measure_pipeline.py` run against a real photo (or are marked "pending" until a
  measurement exists), never estimated or guessed.
