import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database.connection import get_session_local
from app.services.book_service import get_books, CANONICAL_CATEGORIES

db = get_session_local()()
for cat in list(CANONICAL_CATEGORIES.keys()):
    res = get_books(db, category=cat, size=5)
    print(f"Category '{cat}': found {res.total} books")

db.close()
