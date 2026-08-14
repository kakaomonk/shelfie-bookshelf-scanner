"""
One-off script that generated catalog.csv.

Not part of the running app — kept for transparency about how the catalog was built.
Columns: id, title, author, alt_titles, year, publisher.

`alt_titles` is semicolon-separated. `author` is left in whatever form a real library
system would plausibly record it in (this is deliberate — see README's "The catalog"
section for which rows are intentionally messy and why).
"""
import csv
from pathlib import Path

# (title, author, alt_titles, year, publisher)
ROWS = [
    # --- Dune cluster: two editions of book 1, plus title-substring sequels ---
    ("Dune", "Frank Herbert", "", "1965", "Chilton Books"),
    ("Dune", "Frank Herbert", "", "2019", "Ace (movie tie-in edition)"),
    ("Dune Messiah", "Frank Herbert", "", "1969", "G.P. Putnam's Sons"),
    ("Children of Dune", "Frank Herbert", "", "1976", "G.P. Putnam's Sons"),

    # --- 1984: two editions ---
    ("1984", "George Orwell", "Nineteen Eighty-Four", "1949", "Secker & Warburg"),
    ("1984", "George Orwell", "Nineteen Eighty-Four", "1961", "Signet Classics"),

    # --- The Hobbit: two editions ---
    ("The Hobbit", "J.R.R. Tolkien", "The Hobbit, or There and Back Again", "1937", "Allen & Unwin"),
    ("The Hobbit", "J.R.R. Tolkien", "The Hobbit, or There and Back Again", "2012", "Houghton Mifflin"),

    # --- LOTR: omnibus alongside its individual volumes ---
    ("The Lord of the Rings", "J.R.R. Tolkien", "LOTR", "1968", "Allen & Unwin (single-volume omnibus)"),
    ("The Fellowship of the Ring", "J.R.R. Tolkien", "", "1954", "Allen & Unwin"),
    ("The Two Towers", "J.R.R. Tolkien", "", "1954", "Allen & Unwin"),
    ("The Return of the King", "J.R.R. Tolkien", "", "1955", "Allen & Unwin"),

    # --- Narnia: second omnibus + volumes example ---
    ("The Chronicles of Narnia", "C.S. Lewis", "Narnia Omnibus", "2001", "HarperCollins (single-volume omnibus, 7 books)"),
    ("The Lion, the Witch and the Wardrobe", "C.S. Lewis", "", "1950", "Geoffrey Bles"),
    ("Prince Caspian", "C.S. Lewis", "", "1951", "Geoffrey Bles"),

    # --- Harry Potter: same book, two different titles, as separate entries (no alt_titles crutch) ---
    ("Harry Potter and the Philosopher's Stone", "J.K. Rowling", "", "1997", "Bloomsbury"),
    ("Harry Potter and the Sorcerer's Stone", "J.K. Rowling", "", "1998", "Scholastic"),
    ("Harry Potter and the Chamber of Secrets", "J.K. Rowling", "", "1998", "Bloomsbury"),
    ("Harry Potter and the Prisoner of Azkaban", "J.K. Rowling", "", "1999", "Bloomsbury"),
    ("Harry Potter and the Goblet of Fire", "J.K. Rowling", "", "2000", "Bloomsbury"),
    ("Harry Potter and the Order of the Phoenix", "J.K. Rowling", "", "2003", "Bloomsbury"),
    ("Harry Potter and the Half-Blood Prince", "J.K. Rowling", "", "2005", "Bloomsbury"),
    ("Harry Potter and the Deathly Hallows", "J.K. Rowling", "", "2007", "Bloomsbury"),
    # Rowling's crime-fiction pseudonym: same real author, deliberately unlinked (no alt_titles/author
    # cross-reference) since a shelf photo gives no way to know the two are the same person.
    ("The Cuckoo's Calling", "Robert Galbraith", "", "2013", "Mulholland Books"),

    # --- Same title published under two different titles, via alt_titles instead ---
    ("The Golden Compass", "Philip Pullman", "Northern Lights", "1995", "Knopf (US) / Scholastic (UK: Northern Lights)"),

    # --- Foundation cluster: shared title across two unrelated books + title substrings ---
    ("Foundation", "Isaac Asimov", "", "1951", "Gnome Press"),
    ("Foundation and Empire", "Isaac Asimov", "", "1952", "Gnome Press"),
    ("Second Foundation", "Isaac Asimov", "", "1953", "Gnome Press"),
    ("Foundation", "Peter Ackroyd", "The History of England, Volume I", "2011", "Macmillan"),

    # --- Two genuinely different books sharing an exact title ---
    ("The Stranger", "Albert Camus", "L'Étranger", "1942", "Gallimard"),
    ("The Stranger", "Harlan Coben", "", "2015", "Dutton"),

    # --- Short, substring-prone titles ---
    ("It", "Stephen King", "", "1986", "Viking"),
    ("It Ends with Us", "Colleen Hoover", "", "2016", "Atria Books"),
    ("The Shining", "King, Stephen", "", "1977", "Doubleday"),

    # --- Author name in more than one form: accents, order, transliteration ---
    ("One Hundred Years of Solitude", "García Márquez, Gabriel", "Cien años de soledad", "1967", "Harper & Row"),
    ("Love in the Time of Cholera", "Gabriel Garcia Marquez", "El amor en los tiempos del cólera", "1985", "Knopf"),
    ("Crime and Punishment", "Fyodor Dostoevsky", "", "1866", "The Russian Messenger"),
    ("The Brothers Karamazov", "Dostoyevsky, Fyodor M.", "", "1880", "The Russian Messenger"),
    ("War and Peace", "Leo Tolstoy", "", "1869", "The Russian Messenger"),
    ("Anna Karenina", "Tolstoy, Leo", "", "1877", "The Russian Messenger"),

    # --- Common shelf fiction/classics ---
    ("To Kill a Mockingbird", "Harper Lee", "", "1960", "J.B. Lippincott & Co."),
    ("The Great Gatsby", "F. Scott Fitzgerald", "", "1925", "Charles Scribner's Sons"),
    ("Pride and Prejudice", "Jane Austen", "", "1813", "T. Egerton"),
    ("Beloved", "Toni Morrison", "", "1987", "Knopf"),
    ("The Catcher in the Rye", "J.D. Salinger", "", "1951", "Little, Brown and Company"),
    ("Slaughterhouse-Five", "Kurt Vonnegut", "", "1969", "Delacorte Press"),
    ("The Bell Jar", "Sylvia Plath", "", "1963", "Heinemann"),
    ("Middlemarch", "George Eliot", "", "1871", "William Blackwood and Sons"),
    ("Jane Eyre", "Charlotte Bronte", "", "1847", "Smith, Elder & Co."),
    ("Wuthering Heights", "Emily Bronte", "", "1847", "Thomas Cautley Newby"),
    ("Moby-Dick", "Herman Melville", "", "1851", "Harper & Brothers"),
    ("The Grapes of Wrath", "John Steinbeck", "", "1939", "The Viking Press"),
    ("Of Mice and Men", "John Steinbeck", "", "1937", "Covici Friede"),
    ("Don Quixote", "Miguel de Cervantes", "", "1605", "Francisco de Robles"),
    ("The Alchemist", "Paulo Coelho", "O Alquimista", "1988", "HarperTorch"),
    ("Where the Crawdads Sing", "Delia Owens", "", "2018", "G.P. Putnam's Sons"),
    ("The Kite Runner", "Khaled Hosseini", "", "2003", "Riverhead Books"),
    ("Life of Pi", "Yann Martel", "", "2001", "Knopf Canada"),
    ("The Road", "Cormac McCarthy", "", "2006", "Alfred A. Knopf"),
    ("No Country for Old Men", "Cormac McCarthy", "", "2005", "Alfred A. Knopf"),
    ("All the Light We Cannot See", "Anthony Doerr", "", "2014", "Scribner"),
    ("The Book Thief", "Markus Zusak", "", "2005", "Picador"),
    ("The Night Circus", "Erin Morgenstern", "", "2011", "Doubleday"),
    ("Normal People", "Sally Rooney", "", "2018", "Faber & Faber"),
    ("The Handmaid's Tale", "Margaret Atwood", "", "1985", "McClelland and Stewart"),
    ("Never Let Me Go", "Kazuo Ishiguro", "", "2005", "Faber & Faber"),
    ("The Remains of the Day", "Kazuo Ishiguro", "", "1989", "Faber & Faber"),
    ("Klara and the Sun", "Ishiguro, Kazuo", "", "2021", "Faber & Faber"),

    # --- Sci-fi / fantasy ---
    ("Ender's Game", "Orson Scott Card", "", "1985", "Tor Books"),
    ("Neuromancer", "William Gibson", "", "1984", "Ace Books"),
    ("Brave New World", "Aldous Huxley", "", "1932", "Chatto & Windus"),
    ("Fahrenheit 451", "Ray Bradbury", "", "1953", "Ballantine Books"),
    ("The Martian", "Andy Weir", "", "2011", "Crown Publishing"),
    ("Project Hail Mary", "Andy Weir", "", "2021", "Ballantine Books"),
    ("A Game of Thrones", "George R.R. Martin", "", "1996", "Bantam Spectra"),
    ("A Clash of Kings", "George R.R. Martin", "", "1998", "Bantam Spectra"),
    ("Mistborn: The Final Empire", "Brandon Sanderson", "Mistborn", "2006", "Tor Books"),
    ("The Name of the Wind", "Patrick Rothfuss", "", "2007", "DAW Books"),
    ("American Gods", "Neil Gaiman", "", "2001", "William Morrow"),
    ("Good Omens", "Neil Gaiman and Terry Pratchett", "", "1990", "Victor Gollancz"),
    ("The Hitchhiker's Guide to the Galaxy", "Douglas Adams", "", "1979", "Pan Books"),
    ("Circe", "Madeline Miller", "", "2018", "Little, Brown and Company"),
    ("The Song of Achilles", "Madeline Miller", "", "2011", "Ecco"),

    # --- Thriller / mystery ---
    ("Gone Girl", "Gillian Flynn", "", "2012", "Crown Publishing"),
    ("Sharp Objects", "Gillian Flynn", "", "2006", "Shaye Areheart Books"),
    ("The Girl with the Dragon Tattoo", "Stieg Larsson", "Man som hatar kvinnor", "2005", "Norstedts Forlag"),
    ("The Da Vinci Code", "Dan Brown", "", "2003", "Doubleday"),
    ("And Then There Were None", "Agatha Christie", "", "1939", "Collins Crime Club"),
    ("Murder on the Orient Express", "Agatha Christie", "", "1934", "Collins Crime Club"),
    ("The Silent Patient", "Alex Michaelides", "", "2019", "Celadon Books"),
    ("Big Little Lies", "Liane Moriarty", "", "2014", "Penguin"),
    ("The Girl on the Train", "Paula Hawkins", "", "2015", "Doubleday"),

    # --- YA ---
    ("The Hunger Games", "Suzanne Collins", "", "2008", "Scholastic"),
    ("Catching Fire", "Suzanne Collins", "", "2009", "Scholastic"),
    ("Divergent", "Veronica Roth", "", "2011", "Katherine Tegen Books"),
    ("The Fault in Our Stars", "John Green", "", "2012", "Dutton Books"),
    ("Twilight", "Stephenie Meyer", "", "2005", "Little, Brown and Company"),

    # --- Nonfiction / business / self-help / pop-science ---
    ("Sapiens: A Brief History of Humankind", "Yuval Noah Harari", "", "2011", "Harvill Secker"),
    ("Atomic Habits", "James Clear", "", "2018", "Avery"),
    ("Thinking, Fast and Slow", "Daniel Kahneman", "", "2011", "Farrar, Straus and Giroux"),
    ("The Lean Startup", "Eric Ries", "", "2011", "Crown Business"),
    ("Educated", "Tara Westover", "", "2018", "Random House"),
    ("Becoming", "Michelle Obama", "", "2018", "Crown Publishing"),
    ("Outliers", "Malcolm Gladwell", "", "2008", "Little, Brown and Company"),
    ("The Tipping Point", "Malcolm Gladwell", "", "2000", "Little, Brown and Company"),
    ("A Brief History of Time", "Stephen Hawking", "", "1988", "Bantam Books"),
    ("Cosmos", "Carl Sagan", "", "1980", "Random House"),
    ("The Selfish Gene", "Richard Dawkins", "", "1976", "Oxford University Press"),
    ("Man's Search for Meaning", "Viktor E. Frankl", "", "1946", "Verlag fur Jugend und Volk"),
    ("The Power of Habit", "Charles Duhigg", "", "2012", "Random House"),
    ("Freakonomics", "Steven D. Levitt and Stephen J. Dubner", "", "2005", "William Morrow"),

    # --- Children's (common on family shelves) ---
    ("Charlotte's Web", "E.B. White", "", "1952", "Harper & Brothers"),
    ("The Very Hungry Caterpillar", "Eric Carle", "", "1969", "World Publishing Company"),
    ("Where the Wild Things Are", "Maurice Sendak", "", "1963", "Harper & Row"),
]


def main():
    out_path = Path(__file__).resolve().parent.parent / "catalog.csv"
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "title", "author", "alt_titles", "year", "publisher"])
        for i, (title, author, alt_titles, year, publisher) in enumerate(ROWS, start=1):
            writer.writerow([i, title, author, alt_titles, year, publisher])
    print(f"Wrote {len(ROWS)} rows to {out_path}")


if __name__ == "__main__":
    main()
