from django.core.management import call_command
from django.test import TestCase

from scanner.matching import match_book
from scanner.models import CatalogBook


class MatchingAgainstSyntheticCatalogTests(TestCase):
    """Unit tests against a small hand-built catalog, independent of catalog.csv content."""

    def setUp(self):
        self.catalog = [
            CatalogBook(id=1, title='The Great Gatsby', author='F. Scott Fitzgerald', alt_titles=''),
            CatalogBook(id=2, title='The Grapes of Wrath', author='John Steinbeck', alt_titles=''),
        ]

    def test_exact_match_is_high_confidence(self):
        result = match_book('The Great Gatsby', 'F. Scott Fitzgerald', self.catalog)
        self.assertEqual(result['status'], 'matched')
        self.assertEqual(result['best_match'].catalog_id, 1)

    def test_typo_in_title_still_matches(self):
        result = match_book('The Grat Gatsby', 'F. Scott Fitzgerald', self.catalog)
        self.assertEqual(result['best_match'].catalog_id, 1)
        self.assertGreaterEqual(result['best_match'].score, 0.55)

    def test_missing_author_read_lowers_score_but_can_still_match(self):
        with_author = match_book('The Great Gatsby', 'F. Scott Fitzgerald', self.catalog)
        without_author = match_book('The Great Gatsby', '', self.catalog)
        self.assertLess(without_author['best_match'].score, with_author['best_match'].score)
        self.assertFalse(without_author['best_match'].author_read)

    def test_no_plausible_candidate_is_unmatched(self):
        result = match_book('Some Completely Unrelated Title', 'Nobody Real', self.catalog)
        self.assertEqual(result['status'], 'unmatched')

    def test_unmatched_never_suggests_a_fake_best_match(self):
        # Regression test: an illegible spine (empty title AND author) scores exactly 0.0 against
        # every catalog row. Python's stable sort then preserves catalog order among that tie, so
        # whichever row has the lowest id silently "won" and was shown to the user as if it were a
        # real suggestion -- found via a real device test where nearly every unreadable spine came
        # back labeled "Dune" (catalog id 1). 'unmatched' must mean no usable suggestion at all.
        result = match_book('', '', self.catalog)
        self.assertEqual(result['status'], 'unmatched')
        self.assertIsNone(result['best_match'])
        self.assertEqual(result['candidates'], [])


class MatchingAgainstRealCatalogTests(TestCase):
    """Integration tests against the actual catalog.csv shipped in the repo, exercising the
    specific messiness it was built to contain."""

    @classmethod
    def setUpTestData(cls):
        call_command('load_catalog')

    def test_us_uk_alt_title_resolves_via_alt_titles_column(self):
        # Catalog row: title "The Golden Compass", alt_titles "Northern Lights".
        result = match_book('Northern Lights', 'Philip Pullman', CatalogBook.objects.all())
        self.assertEqual(result['status'], 'matched')
        self.assertEqual(result['best_match'].title, 'The Golden Compass')

    def test_author_initials_vs_spelled_out_first_name(self):
        # Catalog author is "J.K. Rowling"; VLM reads the spelled-out form.
        result = match_book(
            'Harry Potter and the Chamber of Secrets', 'Joanne Rowling', CatalogBook.objects.all()
        )
        self.assertEqual(result['status'], 'matched')
        self.assertEqual(result['best_match'].title, 'Harry Potter and the Chamber of Secrets')

    def test_lastname_firstname_author_order_in_catalog(self):
        # Catalog row: author "Dostoyevsky, Fyodor M."; VLM reads natural order, common spelling.
        result = match_book('The Brothers Karamazov', 'Fyodor Dostoevsky', CatalogBook.objects.all())
        self.assertEqual(result['status'], 'matched')
        self.assertEqual(result['best_match'].title, 'The Brothers Karamazov')

    def test_accented_author_matches_unaccented_read(self):
        # Catalog row: author "García Márquez, Gabriel"; VLM read has no accents.
        result = match_book(
            'One Hundred Years of Solitude', 'Gabriel Garcia Marquez', CatalogBook.objects.all()
        )
        self.assertEqual(result['status'], 'matched')
        self.assertEqual(result['best_match'].title, 'One Hundred Years of Solitude')

    def test_shared_exact_title_without_author_is_ambiguous_not_auto_matched(self):
        # Two unrelated books are both titled "Foundation" (Asimov / Ackroyd). If the spine's
        # author line wasn't legible, this must NOT silently auto-match either one.
        result = match_book('Foundation', '', CatalogBook.objects.all())
        self.assertNotEqual(result['status'], 'matched')
        candidate_titles = {c.title for c in result['candidates']}
        self.assertIn('Foundation', candidate_titles)

    def test_shared_exact_title_with_author_disambiguates(self):
        result = match_book('Foundation', 'Isaac Asimov', CatalogBook.objects.all())
        self.assertEqual(result['status'], 'matched')
        self.assertEqual(result['best_match'].author, 'Isaac Asimov')

    def test_title_substring_does_not_falsely_win_over_exact_title(self):
        # "It" (Stephen King) is a literal substring of "It Ends with Us" (Colleen Hoover) --
        # a naive partial-string matcher would prefer the longer title.
        result = match_book('It', 'Stephen King', CatalogBook.objects.all())
        self.assertEqual(result['status'], 'matched')
        self.assertEqual(result['best_match'].title, 'It')
        self.assertEqual(result['best_match'].author, 'Stephen King')

    def test_omnibus_is_not_confused_with_one_of_its_volumes(self):
        # "The Lord of the Rings" (omnibus) vs "The Two Towers" (one of the three volumes it
        # contains) share two of their four words but are meaningfully different catalog entries.
        result = match_book('The Two Towers', 'J.R.R. Tolkien', CatalogBook.objects.all())
        self.assertEqual(result['best_match'].title, 'The Two Towers')

    def test_two_editions_of_the_same_book_both_score_as_a_confident_match(self):
        # Dune has two catalog rows (1965 Chilton / 2019 Ace). A spine read can't tell which
        # printing it is, so either should count as a confident match on title+author alone.
        result = match_book('Dune', 'Frank Herbert', CatalogBook.objects.all())
        self.assertEqual(result['status'], 'matched')
        self.assertEqual(result['best_match'].title, 'Dune')
