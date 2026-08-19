import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database.connection import get_session_local
from app.services.book_service import clean_and_expand_query, get_books
from app.models import Book
from sqlalchemy import select, or_

db = get_session_local()()

test_queries = [
    "horror movies",
    "horror",
    "scary books",
    "stephen king",
    "psychological thriller",
    "movies"
]

for q in test_queries:
    tokens = clean_and_expand_query(q)
    print(f"\nQuery: '{q}' -> Tokens: {tokens}")
    res = get_books(db, query=q, size=5)
    print(f"  Found {res.total} books. Samples:")
    for b in res.items[:3]:
        print(f"    - {b.title} by {b.authors} ({b.categories})")

db.close()
