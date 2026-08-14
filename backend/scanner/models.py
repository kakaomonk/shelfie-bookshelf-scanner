from django.db import models


class CatalogBook(models.Model):
    """A canonical book entry, loaded verbatim from catalog.csv (see scripts/generate_catalog.py).

    The catalog is deliberately messy: it contains duplicate titles across different
    books, multiple editions of the same book, alternate regional titles, and author
    names in inconsistent formats. That's the point — see README's "The catalog" section.
    """

    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    alt_titles = models.CharField(max_length=500, blank=True, default='')
    year = models.CharField(max_length=20, blank=True, default='')
    publisher = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f'{self.title} — {self.author}'


class LibraryEntry(models.Model):
    """A book the user has confirmed into their personal library.

    Deliberately not a review/staging model: scan candidates (including low-confidence
    ones awaiting human review) live only in the API response and the app's in-memory
    state until the user confirms them — nothing unconfirmed is persisted.
    """

    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    catalog_book = models.ForeignKey(
        CatalogBook, null=True, blank=True, on_delete=models.SET_NULL, related_name='library_entries'
    )
    match_confidence = models.FloatField(null=True, blank=True)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-added_at']

    def __str__(self):
        return f'{self.title} — {self.author}'
