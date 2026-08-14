from django.contrib import admin

from .models import CatalogBook, LibraryEntry


@admin.register(CatalogBook)
class CatalogBookAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'author', 'year', 'publisher')
    search_fields = ('title', 'author', 'alt_titles')


@admin.register(LibraryEntry)
class LibraryEntryAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'author', 'catalog_book', 'match_confidence', 'added_at')
