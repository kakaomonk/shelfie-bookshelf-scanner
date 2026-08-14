# Shelfie — Bookshelf → Library Inventory

Turn a photo of a bookshelf into a structured personal library: an Expo app takes the photo,
a Django API finds individual book spines locally, reads title/author off them with a hosted
vision-language model, matches each read against a catalog of canonical books, and asks a human
to confirm anything it isn't confident about.

> Setup steps, architecture, measured latency/cost numbers, catalog rationale, key decisions, and
> what's unfinished are documented below as each piece lands. This section is filled in as the
> project is built, not written up front.

## Project layout

- `backend/` — Django + Django REST Framework API (Python 3.12, CPU-only local model, Claude for
  reading spines, SQLite for storage).
- `frontend/` — Expo (React Native + TypeScript) mobile app.
- `catalog.csv` — the canonical book catalog matched against.
- `test_photos/` — real bookshelf photos used during development.

## Setup

_TODO — filled in once both apps are running end to end._

## Architecture

_TODO_

## Measured latency & cost

_TODO_

## The catalog

_TODO_

## Key decisions & tradeoffs

_TODO_

## What's unfinished

_TODO_
