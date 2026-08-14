"""
Measures real per-image latency and cost for the README's "Numbers" section.

Run from backend/ with the venv active and ANTHROPIC_API_KEY set:

    cd backend && venv/bin/python ../scripts/measure_pipeline.py ../test_photos/shelf_1.jpg

Reports detection time (cold + warm), VLM time, token counts, and an estimated dollar cost
per photo using Claude Haiku's published per-token pricing. Not a benchmark suite -- just
enough real numbers to put in the README instead of guessing.
"""
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django  # noqa: E402

django.setup()

from PIL import Image, ImageOps  # noqa: E402

from scanner.detection import detect_spines  # noqa: E402
from scanner.vlm import read_spines  # noqa: E402

# Claude Haiku 4.5 published pricing, per million tokens (see README for the source/date).
INPUT_COST_PER_MTOK = 1.00
OUTPUT_COST_PER_MTOK = 5.00


def main():
    if len(sys.argv) < 2:
        print('Usage: measure_pipeline.py <path-to-photo> [<path-to-photo> ...]')
        sys.exit(1)

    for path in sys.argv[1:]:
        print(f'\n=== {path} ===')
        image = Image.open(path)
        image = ImageOps.exif_transpose(image).convert('RGB')
        print(f'size: {image.size[0]}x{image.size[1]}')

        t0 = time.monotonic()
        spines = detect_spines(image)
        detection_seconds = time.monotonic() - t0
        print(f'detection (cold, incl. model load): {detection_seconds:.2f}s ({len(spines)} candidates)')

        # Run again in the same process to also report warm (model-loaded) latency.
        t0 = time.monotonic()
        spines_warm = detect_spines(image)
        detection_warm_seconds = time.monotonic() - t0
        print(f'detection (warm, same process): {detection_warm_seconds:.2f}s ({len(spines_warm)} candidates)')

        if not spines:
            print('No spines detected -- skipping VLM read.')
            continue

        t0 = time.monotonic()
        reads, meta = read_spines([s.crop for s in spines])
        vlm_seconds = time.monotonic() - t0
        print(f'VLM read: {vlm_seconds:.2f}s (reported: {meta.get("elapsed_seconds", 0):.2f}s)')
        print(f'  ok={meta.get("ok")} error={meta.get("error")}')

        in_tok = meta.get('input_tokens')
        out_tok = meta.get('output_tokens')
        if in_tok and out_tok:
            cost = (in_tok / 1_000_000) * INPUT_COST_PER_MTOK + (out_tok / 1_000_000) * OUTPUT_COST_PER_MTOK
            print(f'  tokens: {in_tok} in / {out_tok} out -> est. ${cost:.4f} per photo')

        legible_count = sum(1 for r in reads if r.legible)
        print(f'legible reads: {legible_count}/{len(reads)}')
        for r in reads:
            if r.legible:
                print(f'  [{r.index}] "{r.title}" — {r.author}')


if __name__ == '__main__':
    main()
