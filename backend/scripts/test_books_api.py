from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent))

from app.database.connection import get_db
from app.models import User
from app.services import book_service, auth_service
from app.schemas.book import BookListResponse
from app.schemas.auth import LoginRequest
from app.routes import books, ratings
from app.schemas.rating import RatingCreateRequest

def test_stage4():
    db = next(get_db())

    # 1. Test List Books
    res = book_service.get_books(db, query="Birdsong", page=1, size=5)
    print(f"Book search query='Birdsong': found {res.total} items")
    assert res.total >= 1
    sample_isbn = res.items[0].isbn10
    print(f"Sample ISBN: {sample_isbn}, title: {res.items[0].title}")

    # 2. Test Get Book Detail
    book = book_service.get_book_by_isbn(db, sample_isbn)
    assert book is not None
    print(f"Fetched book detail by ISBN: {book.title}")

    # 3. Test Categories
    cats = book_service.get_unique_categories(db)
    print(f"Unique categories count: {len(cats)}, sample: {cats[:5]}")
    assert len(cats) > 0

    # 4. Test Rating submit & fetch
    login_req = LoginRequest(roll_number="276804", password="LibraryUser@276804")
    token_resp = auth_service.login_user(db, login_req)
    user = db.get(User, "276804")

    rate_payload = RatingCreateRequest(isbn10=sample_isbn, rating=9)
    rating_res = ratings.add_or_update_rating(rate_payload, current_user=user, db=db)
    print(f"Added rating: user={rating_res.roll_number}, isbn10={rating_res.isbn10}, rating={rating_res.rating}")
    assert rating_res.rating == 9

    my_ratings = ratings.get_my_ratings(current_user=user, db=db)
    print(f"User ratings count: {len(my_ratings)}")
    assert len(my_ratings) >= 1

    print("\nStage 4 APIs Tested Successfully!")

if __name__ == "__main__":
    test_stage4()
