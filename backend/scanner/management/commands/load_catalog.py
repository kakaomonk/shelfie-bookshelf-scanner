import csv
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from scanner.models import CatalogBook

CATALOG_PATH = Path(settings.BASE_DIR).parent / 'catalog.csv'


class Command(BaseCommand):
    help = 'Load catalog.csv (repo root) into the CatalogBook table, replacing any existing rows.'

    def handle(self, *args, **options):
        if not CATALOG_PATH.exists():
            self.stderr.write(self.style.ERROR(f'catalog.csv not found at {CATALOG_PATH}'))
            return

        with CATALOG_PATH.open(newline='', encoding='utf-8') as f:
            rows = list(csv.DictReader(f))

        CatalogBook.objects.all().delete()
        CatalogBook.objects.bulk_create(
            CatalogBook(
                id=int(row['id']),
                title=row['title'],
                author=row['author'],
                alt_titles=row['alt_titles'],
                year=row['year'],
                publisher=row['publisher'],
            )
            for row in rows
        )
        self.stdout.write(self.style.SUCCESS(f'Loaded {len(rows)} catalog entries from {CATALOG_PATH.name}'))
