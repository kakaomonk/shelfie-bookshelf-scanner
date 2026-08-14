import time
import uuid
from pathlib import Path

from django.conf import settings
from PIL import Image, ImageOps, UnidentifiedImageError
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .detection import detect_spines
from .matching import match_book
from .models import CatalogBook, LibraryEntry
from .vlm import SpineRead, read_spines


@api_view(['GET'])
def health(request):
    return Response({'status': 'ok'})


def _serialize_library_entry(entry):
    return {
        'id': entry.id,
        'title': entry.title,
        'author': entry.author,
        'catalog_id': entry.catalog_book_id,
        'match_confidence': entry.match_confidence,
        'added_at': entry.added_at.isoformat(),
    }


@api_view(['GET', 'POST'])
def library(request):
    """List the user's confirmed library, or confirm one book into it.

    There's no separate "pending review" model: candidates from /api/scan live only in the API
    response and the app's in-memory state while the user reviews them. Nothing is persisted
    unless/until the user actually confirms it here -- so a LibraryEntry is always something a
    person looked at and accepted, never something the pipeline guessed.
    """
    if request.method == 'GET':
        return Response([_serialize_library_entry(e) for e in LibraryEntry.objects.all()])

    title = (request.data.get('title') or '').strip()
    author = (request.data.get('author') or '').strip()
    if not title:
        return Response({'error': 'title is required'}, status=status.HTTP_400_BAD_REQUEST)

    catalog_book = None
    catalog_id = request.data.get('catalog_id')
    if catalog_id:
        try:
            catalog_book = CatalogBook.objects.filter(id=int(catalog_id)).first()
        except (TypeError, ValueError):
            return Response({'error': 'catalog_id must be an integer.'}, status=status.HTTP_400_BAD_REQUEST)

    match_confidence = request.data.get('match_confidence')
    if match_confidence is not None:
        try:
            match_confidence = float(match_confidence)
        except (TypeError, ValueError):
            return Response({'error': 'match_confidence must be a number.'}, status=status.HTTP_400_BAD_REQUEST)

    entry = LibraryEntry.objects.create(
        title=title,
        author=author,
        catalog_book=catalog_book,
        match_confidence=match_confidence,
    )
    return Response(_serialize_library_entry(entry), status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
def library_detail(request, pk):
    entry = LibraryEntry.objects.filter(pk=pk).first()
    if entry is None:
        return Response({'error': 'Library entry not found.'}, status=status.HTTP_404_NOT_FOUND)
    entry.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


def _serialize_candidate(candidate):
    return {
        'catalog_id': candidate.catalog_id,
        'title': candidate.title,
        'author': candidate.author,
        'score': round(candidate.score, 3),
    }


def _serialize_match(match):
    return {
        'status': match['status'],
        'best_match': _serialize_candidate(match['best_match']) if match['best_match'] else None,
        'candidates': [_serialize_candidate(c) for c in match['candidates']],
    }


@api_view(['POST'])
def scan(request):
    """Photo in, structured book candidates out. Never raises past this point -- any pipeline
    failure degrades to a 200 with a `warnings` entry and an empty/partial `books` list, so the
    app always has something sane to render instead of a blank screen or a crash.
    """
    photo = request.FILES.get('photo')
    if photo is None:
        return Response(
            {'error': 'No photo uploaded. Expected a multipart field named "photo".'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        image = Image.open(photo)
        image.load()  # decode now, so a corrupt/truncated upload fails here with a clear error
    except (UnidentifiedImageError, OSError) as exc:
        return Response({'error': f'Could not read the uploaded photo: {exc}'}, status=status.HTTP_400_BAD_REQUEST)

    image = ImageOps.exif_transpose(image)  # phone photos carry an EXIF rotation flag, not rotated pixels

    warnings = []
    scan_dir = Path(settings.MEDIA_ROOT) / 'scans'
    scan_dir.mkdir(parents=True, exist_ok=True)
    stem = uuid.uuid4().hex[:12]

    try:
        image.convert('RGB').save(scan_dir / f'{stem}.jpg', format='JPEG', quality=90)
    except OSError:
        pass  # a saved copy is only for debugging; never fail the scan over it

    t0 = time.monotonic()
    try:
        spines = detect_spines(image)
    except Exception as exc:  # local model is off-the-shelf but still third-party code; never trust it blindly
        return Response(
            {
                'warnings': [f'Spine detection failed: {exc}'],
                'books': [],
                'timing': {},
            }
        )
    detection_seconds = time.monotonic() - t0

    if not spines:
        return Response(
            {
                'warnings': ['No book spines were detected in this photo. Try a closer, more level shot of the shelf.'],
                'books': [],
                'timing': {'detection_seconds': round(detection_seconds, 3)},
            }
        )

    crop_urls = []
    for spine in spines:
        crop_name = f'{stem}_spine_{spine.index}.jpg'
        try:
            spine.crop.save(scan_dir / crop_name, format='JPEG', quality=90)
            crop_urls.append(settings.MEDIA_URL + f'scans/{crop_name}')
        except OSError:
            crop_urls.append(None)

    t1 = time.monotonic()
    try:
        reads, vlm_meta = read_spines([spine.crop for spine in spines])
    except Exception as exc:  # read_spines already catches API/parse errors; this is a last resort
        reads = [SpineRead(i, '', '', False) for i in range(len(spines))]
        vlm_meta = {'ok': False, 'error': f'{type(exc).__name__}: {exc}'}
    vlm_seconds = time.monotonic() - t1

    if not vlm_meta.get('ok', True):
        warnings.append(f"Couldn't read spine text: {vlm_meta.get('error')}")
    if vlm_meta.get('parse_error'):
        warnings.append(f"Some spine reads may be incomplete: {vlm_meta['parse_error']}")
    if vlm_meta.get('dropped_spines'):
        warnings.append(f"{vlm_meta['dropped_spines']} spine(s) were skipped (over the per-scan limit).")

    catalog_books = list(CatalogBook.objects.all())
    books = []
    for spine, read, crop_url in zip(spines, reads, crop_urls):
        match = match_book(read.title, read.author, catalog_books)
        books.append(
            {
                'index': spine.index,
                'bbox': list(spine.bbox),
                'crop_url': crop_url,
                'detection_score': round(spine.score, 3),
                'read': {'title': read.title, 'author': read.author, 'legible': read.legible},
                'match': _serialize_match(match),
            }
        )

    return Response(
        {
            'warnings': warnings,
            'books': books,
            'timing': {
                'detection_seconds': round(detection_seconds, 3),
                'vlm_seconds': round(vlm_seconds, 3),
                'vlm_input_tokens': vlm_meta.get('input_tokens'),
                'vlm_output_tokens': vlm_meta.get('output_tokens'),
            },
        }
    )
