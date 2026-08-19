from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent))

from app.database.connection import get_db
from app.ml.llm_assistant import llm_assistant

def test_chat():
    db = next(get_db())

    # Query 1: Sad emotion + search query
    res1 = llm_assistant.process_chat(db, "I feel sad today. Can you recommend some uplifting fiction or classic stories?")
    print(f"Chat response (Emotion: {res1['emotion']}):")
    print(res1['response'])
    print(f"Suggested books count: {len(res1['suggested_books'])}\n")
    assert len(res1['suggested_books']) > 0

    # Query 2: Specific search
    res2 = llm_assistant.process_chat(db, "Birdsong")
    print(f"Chat response for 'Birdsong':")
    print(res2['response'])
    print(f"Suggested books count: {len(res2['suggested_books'])}\n")
    assert len(res2['suggested_books']) > 0

    print("Stage 6 Chat Assistant Tested Successfully!")

if __name__ == "__main__":
    test_chat()
