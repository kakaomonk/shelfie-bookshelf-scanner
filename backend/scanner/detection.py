"""
Local, off-the-shelf, CPU spine detection.

Model choice: FastSAM (Ultralytics), not a COCO-pretrained detector. COCO's single "book" class
was annotated on isolated books/stacks, and in practice a detector trained on it tends to draw
one or two boxes around a whole shelf rather than one per spine -- there's little training signal
for "many thin adjacent objects." FastSAM is a class-agnostic, prompt-free segmenter: it proposes
a mask for every visually distinct region by color/texture boundary, which is exactly what
separates adjacent spines. We never train or fine-tune it -- pretrained weights, as required.

FastSAM over-generates: it also segments shelves, gaps, decorations, and reflections. We turn its
raw masks into spine candidates with plain geometric heuristics (aspect ratio, size bounds, our
own NMS pass) rather than a second model, since these are cheap, deterministic, and easy to defend
line by line.
"""
import threading
from dataclasses import dataclass
from typing import List, Tuple

from PIL import Image

_MODEL_LOCK = threading.Lock()
_model = None

IMG_SIZE = 1024
CONF_THRESHOLD = 0.35
INTERNAL_IOU = 0.9  # FastSAM's own NMS during inference; kept permissive, we NMS again ourselves

MIN_ASPECT_RATIO = 1.2  # height / width -- spines stand taller than they are wide
MIN_AREA_FRAC = 0.004  # drop slivers/noise
MAX_AREA_FRAC = 0.35  # drop whole-shelf/background blobs
NMS_IOU_THRESHOLD = 0.5
CROP_PADDING_FRAC = 0.04  # small margin so OCR/VLM isn't reading right up to a hard mask edge


def _get_model():
    global _model
    if _model is None:
        with _MODEL_LOCK:
            if _model is None:
                from ultralytics import FastSAM

                _model = FastSAM('FastSAM-s.pt')
    return _model


@dataclass
class SpineCandidate:
    index: int
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2 in original-image pixel coordinates
    score: float
    crop: Image.Image


def _iou(a, b) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
    intersection = iw * ih
    if intersection == 0:
        return 0.0
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    union = area_a + area_b - intersection
    return intersection / union if union else 0.0


def _non_max_suppress(boxes_with_scores, iou_threshold: float):
    ordered = sorted(boxes_with_scores, key=lambda item: item[1], reverse=True)
    kept = []
    for box, score in ordered:
        if all(_iou(box, kept_box) < iou_threshold for kept_box, _ in kept):
            kept.append((box, score))
    return kept


def detect_spines(image: Image.Image) -> List[SpineCandidate]:
    """Find individual book-spine regions in a bookshelf photo.

    Returns an empty list if nothing plausible is found (e.g. not a bookshelf) -- callers must
    treat that as a normal, user-facing outcome, not an error.
    """
    image = image.convert('RGB')
    width, height = image.size
    image_area = width * height

    model = _get_model()
    results = model.predict(
        image,
        device='cpu',
        imgsz=IMG_SIZE,
        conf=CONF_THRESHOLD,
        iou=INTERNAL_IOU,
        retina_masks=True,
        verbose=False,
    )
    result = results[0]
    if result.boxes is None or len(result.boxes) == 0:
        return []

    boxes = result.boxes.xyxy.tolist()
    scores = result.boxes.conf.tolist()

    candidates = []
    for (x1, y1, x2, y2), score in zip(boxes, scores):
        w, h = x2 - x1, y2 - y1
        if w <= 0 or h <= 0:
            continue
        area_frac = (w * h) / image_area
        if not (MIN_AREA_FRAC <= area_frac <= MAX_AREA_FRAC):
            continue
        if (h / w) < MIN_ASPECT_RATIO:
            continue
        candidates.append(((x1, y1, x2, y2), score))

    kept = _non_max_suppress(candidates, NMS_IOU_THRESHOLD)
    # Left-to-right, matching how a person reads spines along a shelf.
    kept.sort(key=lambda item: item[0][0])

    spine_candidates = []
    for i, (box, score) in enumerate(kept):
        x1, y1, x2, y2 = box
        pad_x, pad_y = (x2 - x1) * CROP_PADDING_FRAC, (y2 - y1) * CROP_PADDING_FRAC
        crop_box = (
            max(0, int(x1 - pad_x)),
            max(0, int(y1 - pad_y)),
            min(width, int(x2 + pad_x)),
            min(height, int(y2 + pad_y)),
        )
        spine_candidates.append(
            SpineCandidate(
                index=i,
                bbox=(int(x1), int(y1), int(x2), int(y2)),
                score=float(score),
                crop=image.crop(crop_box),
            )
        )
    return spine_candidates
