from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent))

from app.database.connection import get_db
from app.ml.llm_assistant import llm_assistant, get_simulated_availability, session_store
from app.ml.recommendation import recommendation_engine
from app.models import User

def test_user_isolation_and_availability():
    db = next(get_db())

    print("=== 1. Testing Chat User Isolation ===")
    user_a_session = "sess_276804_12345"
    user_b_session = "sess_276805_67890"

    # User A asks for fantasy
    res_a = llm_assistant.process_chat(db, "Recommend fantasy novels", session_id=user_a_session)
    session_a = session_store.get_session(user_a_session)
    print(f"User A history count: {len(session_a['history'])}")

    # User B should have an empty session history initially
    session_b = session_store.get_session(user_b_session)
    print(f"User B initial history count: {len(session_b['history'])}")
    assert len(session_b['history']) == 0, "User B should not have User A's history"

    # Verify suggested_books in res_a are all available and matched
    for b in res_a["suggested_books"]:
        assert b["is_available"] is True, f"Suggested book {b['title']} must be available"
        assert b["copies_available"] > 0, f"Suggested book {b['title']} must have >0 copies"
        print(f"  [OK] User A matched available book: {b['title']} ({b['copies_available']} copies)")

    print("\n=== 2. Testing Recommendations Availability ===")
    recs = recommendation_engine.recommend_for_user(db, roll_number="276804", top_n=10)
    print(f"Generated {len(recs)} recommendations for 276804:")
    for r in recs:
        total, avail, is_avail = get_simulated_availability(r.isbn10, r.title)
        assert is_avail is True, f"Recommended book {r.title} must be available"
        assert avail > 0, f"Recommended book {r.title} must have >0 available copies"
        print(f"  [OK] [{r.isbn10}] {r.title} (Available: {avail}/{total})")

    print("\n=== 3. Testing Chatbot Specific Suggestion Matching ===")
    # Asking a pure conversational question shouldn't attach phantom book cards
    res_smalltalk = llm_assistant.process_chat(db, "Thank you so much!", session_id=user_a_session)
    print(f"Response to 'Thank you so much!': {res_smalltalk['response']}")
    print(f"Suggested books count for smalltalk: {len(res_smalltalk['suggested_books'])}")
    assert len(res_smalltalk['suggested_books']) == 0, "Chit-chat / thank you should not have suggested book cards"

    print("\nAll User Isolation and Chatbot Availability Tests Passed Successfully!")

if __name__ == "__main__":
    test_user_isolation_and_availability()
