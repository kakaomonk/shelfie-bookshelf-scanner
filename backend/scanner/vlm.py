"""
Reading title/author off spine crops with a hosted vision-language model.

Division of labor with the local model (scanner/detection.py): FastSAM finds *where* the spines
are -- geometry, no reading comprehension needed, so it runs locally on CPU for free. Reading the
actual text needs real language+vision understanding (angled text, stylized fonts, partial
occlusion), which is what the hosted model is for. Doing detection locally instead of also paying
per-crop for "find the spines" cuts both latency and cost -- see the README for measured numbers.

All spine crops from one photo are sent in a *single* Claude API call (multiple images, one
message) instead of one call per spine. A shelf can easily hold 20-30 books; batching turns that
into one round trip instead of 20-30, which matters far more for latency and cost than it does for
accuracy here.

The model is forced to respond via tool use (report_spine_reads) rather than asked to produce
freeform JSON in prose -- this is what makes "malformed JSON back from the model" a rare edge case
instead of the common case, but we still don't trust it blindly: anything unparseable becomes an
illegible read, never a crash.
"""
import base64
import io
import time
from dataclasses import dataclass
from typing import List

import anthropic
from django.conf import settings

MODEL = 'claude-haiku-4-5-20251001'
MAX_SPINES_PER_CALL = 30
REQUEST_TIMEOUT_SECONDS = 45.0

TOOL_SCHEMA = {
    'name': 'report_spine_reads',
    'description': 'Report what could be read on each numbered book spine crop.',
    'input_schema': {
        'type': 'object',
        'properties': {
            'reads': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {
                        'index': {
                            'type': 'integer',
                            'description': 'The spine number, matching the label before its image.',
                        },
                        'title': {
                            'type': 'string',
                            'description': 'Book title as printed on the spine, or "" if not legible.',
                        },
                        'author': {
                            'type': 'string',
                            'description': 'Author name as printed on the spine, or "" if not legible.',
                        },
                        'legible': {
                            'type': 'boolean',
                            'description': 'False if nothing useful could be read on this spine.',
                        },
                    },
                    'required': ['index', 'title', 'author', 'legible'],
                },
            },
        },
        'required': ['reads'],
    },
}

INSTRUCTIONS = (
    'Each image below is a cropped photo of a single book spine, numbered in order. '
    'For every numbered spine, read the title and author exactly as printed. '
    "Spines are often thin, angled, or partly cut off -- if you can't confidently read real "
    'text, set legible=false and leave title/author as empty strings. Do not invent or guess '
    'a plausible-sounding title or author; an empty read is far better than a wrong one. '
    'Call report_spine_reads with exactly one entry per spine, in the same order.'
)


@dataclass
class SpineRead:
    index: int
    title: str
    author: str
    legible: bool


def _encode_image(image) -> dict:
    buf = io.BytesIO()
    image.convert('RGB').save(buf, format='JPEG', quality=90)
    return {
        'type': 'image',
        'source': {
            'type': 'base64',
            'media_type': 'image/jpeg',
            'data': base64.standard_b64encode(buf.getvalue()).decode('utf-8'),
        },
    }


def _illegible_reads(count: int) -> List[SpineRead]:
    return [SpineRead(i, '', '', False) for i in range(count)]


def read_spines(crops: list):
    """Read title/author off each spine crop with a single batched Claude call.

    Returns (reads, meta). `reads` always has exactly len(crops) entries, in the same order as
    `crops`, so callers can zip them back against bounding boxes unconditionally. On any failure
    (missing API key, timeout, API error, unparseable response) every entry is legible=False --
    the caller surfaces those for manual entry, never as a crash. `meta` carries timing/token
    counts for the latency/cost report and flags anything dropped or gone wrong.
    """
    if not crops:
        return [], {'ok': True, 'elapsed_seconds': 0.0, 'input_images': 0}

    if not settings.ANTHROPIC_API_KEY:
        return (
            _illegible_reads(len(crops)),
            {'ok': False, 'error': 'ANTHROPIC_API_KEY not configured', 'elapsed_seconds': 0.0, 'input_images': len(crops)},
        )

    sent_crops = crops[:MAX_SPINES_PER_CALL]
    dropped = len(crops) - len(sent_crops)

    content = []
    for i, crop in enumerate(sent_crops):
        content.append({'type': 'text', 'text': f'Spine {i}:'})
        content.append(_encode_image(crop))
    content.append({'type': 'text', 'text': INSTRUCTIONS})

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY, timeout=REQUEST_TIMEOUT_SECONDS)

    start = time.monotonic()
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            tools=[TOOL_SCHEMA],
            tool_choice={'type': 'tool', 'name': 'report_spine_reads'},
            messages=[{'role': 'user', 'content': content}],
        )
    except anthropic.AnthropicError as exc:
        elapsed = time.monotonic() - start
        return (
            _illegible_reads(len(crops)),
            {
                'ok': False,
                'error': f'{type(exc).__name__}: {exc}',
                'elapsed_seconds': elapsed,
                'input_images': len(sent_crops),
                'dropped_spines': dropped,
            },
        )

    elapsed = time.monotonic() - start
    reads_by_index = {}
    parse_error = None
    try:
        tool_use = next(block for block in response.content if block.type == 'tool_use')
        for entry in tool_use.input.get('reads', []):
            idx = int(entry.get('index'))
            reads_by_index[idx] = SpineRead(
                index=idx,
                title=(entry.get('title') or '').strip(),
                author=(entry.get('author') or '').strip(),
                legible=bool(entry.get('legible')),
            )
    except (StopIteration, ValueError, TypeError, AttributeError, KeyError) as exc:
        # Anything not covered below (e.g. an index the model skipped) just falls through as an
        # illegible read, not an error -- but we still record that parsing was incomplete.
        parse_error = f'{type(exc).__name__}: {exc}'

    reads = [reads_by_index.get(i, SpineRead(i, '', '', False)) for i in range(len(crops))]
    usage = getattr(response, 'usage', None)
    meta = {
        'ok': True,
        'elapsed_seconds': elapsed,
        'input_images': len(sent_crops),
        'dropped_spines': dropped,
        'parse_error': parse_error,
        'input_tokens': getattr(usage, 'input_tokens', None),
        'output_tokens': getattr(usage, 'output_tokens', None),
    }
    return reads, meta
