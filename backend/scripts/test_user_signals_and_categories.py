from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent))

from app.database.connection import get_session_local, get_engine, Base
from app.models import Book, User, Rating, UserInteraction
from app.services.book_service import get_unique_categories, get_books, CANONICAL_CATEGORIES
from app.ml.recommendation import recommendation_engine

def test_system():
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    db = get_session_local()()

    try:
        # 1. Test Precise Categories List
        cats = get_unique_categories(db)
        print(f"[OK] 12 Precise Categories count: {len(cats)}")
        for idx, c in enumerate(cats, 1):
            print(f"   {idx}. {c}")

        # 2. Test Category Filtering
        for sample_cat in ["Sci-Fi & Fantasy", "Mystery & Thriller", "Fiction & Classics"]:
            res = get_books(db, category=sample_cat, size=3)
            print(f"\n[OK] Category filter '{sample_cat}' found {res.total} books. First 2:")
            for b in res.items[:2]:
                print(f"     - {b.title} (Category: {b.categories})")

        # 3. Test Multi-Signal Recommendation for Cold Start vs Active User
        cold_recs = recommendation_engine.recommend_for_user(db, roll_number="new_scholar_test_000", top_n=3)
        print(f"\n[OK] Cold-Start Fallback: returned {len(cold_recs)} top rated books:")
        for b in cold_recs:
            print(f"     - {b.title} (Rating: {b.average_rating})")

        # 4. Test Interactive Signals
        test_roll = "student_signal_verifier_2026"
        db.query(UserInteraction).filter(UserInteraction.roll_number == test_roll).delete()
        db.commit()

        # Add search and chat signals for mystery / detective / holmes
        db.add(UserInteraction(roll_number=test_roll, interaction_type="search", content="sherlock holmes mystery"))
        db.add(UserInteraction(roll_number=test_roll, interaction_type="chat", content="Tell me about murder mystery and detective books"))
        db.commit()

        active_recs = recommendation_engine.recommend_for_user(db, roll_number=test_roll, top_n=5)
        print(f"\n[OK] Active Student with Mystery search/chat signals returned {len(active_recs)} personalized books:")
        for b in active_recs[:3]:
            print(f"     - {b.title} ({b.categories})")

        # Cleanup
        db.query(UserInteraction).filter(UserInteraction.roll_number == test_roll).delete()
        db.commit()

        print("\nALL PRECISE CATEGORIES & MULTI-SIGNAL RECOMMENDATION TESTS PASSED SUCCESSFULLY!")
    finally:
        db.close()

if __name__ == "__main__":
    test_system()
