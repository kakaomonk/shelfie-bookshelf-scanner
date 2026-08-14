"""
Fuzzy matching between a VLM's read of a book spine and the catalog.

Design notes (see README "Key decisions & tradeoffs" for the full writeup):

- Title and author are scored independently, then combined, because a VLM read of a spine
  routinely nails the title but garbles or omits the author (thin spines rarely have room for a
  full author name).
- Title similarity uses token_sort_ratio (order-independent) rather than partial_ratio, because
  partial_ratio treats "Foundation" as a perfect match against "Foundation and Empire" (it's a
  literal substring) -- exactly the failure mode the catalog's substring cases are designed to
  expose. token_sort_ratio is combined with a length-ratio penalty so a short read isn't scored
  as a near-perfect match against a much longer catalog title.
- Author strings are normalized for "Lastname, Firstname" order and scored mostly on last name,
  since first names routinely differ in form (initials vs. spelled out) even when it's clearly
  the same person -- the catalog has both.
- A missing author read isn't scored as a mismatch; it's scored as *no signal*, with a small
  penalty on the overall score to reflect the missing corroboration.
- Two catalog entries that both score close to the top *and describe different books* (e.g.
  Asimov's "Foundation" and Ackroyd's "Foundation" when the author wasn't legible) are treated as
  an ambiguous tie and forced to human review even if the top score alone would clear the
  auto-match bar. A tie between two rows for the same book (e.g. two Dune editions) is not treated
  as ambiguous -- any edition is an equally correct answer since a spine gives no way to tell them
  apart, so it auto-matches to the higher-ranked row.
"""
import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable, Optional

from rapidfuzz import fuzz

HIGH_CONFIDENCE_THRESHOLD = 0.90
LOW_CONFIDENCE_THRESHOLD = 0.55
TIE_MARGIN = 0.05

TITLE_WEIGHT = 0.65
AUTHOR_WEIGHT = 0.35

NO_AUTHOR_SIGNAL_PENALTY = 0.9


def _strip_accents(s: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))


def _normalize(s: str) -> str:
    s = _strip_accents(s or '').lower()
    s = re.sub(r'[^a-z0-9,\s]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def _normalize_author(raw: str):
    """Return (full_normalized, last_name_guess), handling 'Lastname, Firstname' order."""
    s = _normalize(raw)
    if ',' in s:
        last, _, rest = s.partition(',')
        last = last.strip()
        rest = rest.strip()
        full = f'{rest} {last}'.strip()
    else:
        full = s
        last = s.split()[-1] if s.split() else ''
    return full, last


def title_score(read_title: str, catalog_title: str, alt_titles: str = '') -> float:
    a = _normalize(read_title)
    if not a:
        return 0.0
    candidates = [catalog_title] + [t for t in (alt_titles or '').split(';') if t.strip()]
    best = 0.0
    for cand in candidates:
        b = _normalize(cand)
        if not b:
            continue
        similarity = fuzz.token_sort_ratio(a, b) / 100
        length_penalty = min(len(a), len(b)) / max(len(a), len(b))
        best = max(best, similarity * (0.5 + 0.5 * length_penalty))
    return best


def author_score(read_author: str, catalog_author: str) -> float:
    if not read_author or not catalog_author:
        return 0.0
    full_a, last_a = _normalize_author(read_author)
    full_b, last_b = _normalize_author(catalog_author)
    last_sim = fuzz.ratio(last_a, last_b) / 100 if last_a and last_b else 0.0
    full_sim = fuzz.token_sort_ratio(full_a, full_b) / 100
    return 0.6 * last_sim + 0.4 * full_sim


@dataclass
class MatchCandidate:
    catalog_id: int
    title: str
    author: str
    score: float
    title_score: float
    author_score: float
    author_read: bool


def score_candidate(read_title: str, read_author: Optional[str], catalog_book) -> MatchCandidate:
    t_score = title_score(read_title, catalog_book.title, catalog_book.alt_titles)
    author_read = bool(read_author and read_author.strip())
    if author_read:
        a_score = author_score(read_author, catalog_book.author)
        overall = TITLE_WEIGHT * t_score + AUTHOR_WEIGHT * a_score
    else:
        a_score = 0.0
        overall = t_score * NO_AUTHOR_SIGNAL_PENALTY
    return MatchCandidate(
        catalog_id=catalog_book.id,
        title=catalog_book.title,
        author=catalog_book.author,
        score=overall,
        title_score=t_score,
        author_score=a_score,
        author_read=author_read,
    )


def match_book(read_title: str, read_author: Optional[str], catalog_books: Iterable, top_n: int = 3) -> dict:
    """Score `catalog_books` against a single VLM read and classify the result.

    Returns {'status': 'matched' | 'review' | 'unmatched', 'best_match': MatchCandidate | None,
    'candidates': [MatchCandidate, ...]}. 'matched' means auto-add; 'review' and 'unmatched' both
    require a human decision -- the difference is only which state the review screen defaults to.
    """
    scored = sorted(
        (score_candidate(read_title, read_author, book) for book in catalog_books),
        key=lambda c: c.score,
        reverse=True,
    )
    top = scored[:top_n]
    if not top:
        return {'status': 'unmatched', 'best_match': None, 'candidates': []}

    best = top[0]
    runner_up = top[1] if len(top) > 1 else None
    # A tie only means genuine ambiguity if the tied rows describe different books. Two catalog
    # rows for different *editions* of the same book (identical title+author) tie constantly and
    # aren't a real decision for the user -- any edition is an equally correct answer here.
    ambiguous_tie = (
        runner_up is not None
        and (best.score - runner_up.score) < TIE_MARGIN
        and runner_up.score >= LOW_CONFIDENCE_THRESHOLD
        and (best.title, best.author) != (runner_up.title, runner_up.author)
    )

    if best.score >= HIGH_CONFIDENCE_THRESHOLD and not ambiguous_tie:
        status = 'matched'
    elif best.score >= LOW_CONFIDENCE_THRESHOLD:
        status = 'review'
    else:
        status = 'unmatched'

    # 'unmatched' must mean "no usable suggestion", not "here's whichever catalog row happened to
    # sort first." Without this, an illegible read (empty title AND author) scores exactly 0.0
    # against every catalog row; Python's stable sort then keeps catalog order among the tie, so
    # the lowest-id row -- Dune, id 1 -- silently won and got shown as a "suggested" match on every
    # unreadable spine. Caught via a real device test where nearly everything came back as Dune.
    if status == 'unmatched':
        return {'status': status, 'best_match': None, 'candidates': []}

    return {'status': status, 'best_match': best, 'candidates': top}
