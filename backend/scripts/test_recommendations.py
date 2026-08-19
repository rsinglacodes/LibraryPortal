from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent))

from app.database.connection import get_db
from app.ml.recommendation import recommendation_engine
from app.models import User

def test_recommendations():
    db = next(get_db())
    user = db.get(User, "276804")
    assert user is not None

    recs = recommendation_engine.recommend_for_user(db, roll_number="276804", top_n=5)
    print(f"Generated {len(recs)} recommendations for user 276804:")
    for idx, r in enumerate(recs, 1):
        print(f"  {idx}. [{r.isbn10}] {r.title} - {r.authors} (Avg rating: {r.average_rating})")

    assert len(recs) == 5
    print("\nStage 5 Recommendation Integration Tested Successfully!")

if __name__ == "__main__":
    test_recommendations()
