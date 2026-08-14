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
  hidden (see README "What's unfinished").
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

## What AI did not do

- Did not fine-tune or train any model -- the brief explicitly forbids it, and no attempt was
  made to work around that.
- Did not pick the hosted VLM provider or spend real API budget without the author's explicit
  say-so.
- Did not fabricate the latency/cost numbers in the README -- they come from
  `scripts/measure_pipeline.py` run against a real photo (or are marked "pending" until a
  measurement exists), never estimated or guessed.
