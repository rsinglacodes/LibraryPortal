import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database.connection import get_session_local
from app.ml.llm_assistant import llm_assistant, detect_emotion

db = get_session_local()()

test_prompts = [
    ("horror movie inquiry", "I love horror movies and scary thrillers, recommend me some terrifying horror books from the library"),
    ("sad emotional tone", "I had a really sad and stressful day, need something heartwarming to lift my mood"),
    ("curious science inquiry", "I am curious to learn about quantum physics and cosmic mysteries"),
]

print("=" * 70)
print("TESTING CHATBOT EMOTION DETECTION & TONE-AWARE OUTPUT")
print("=" * 70)

for label, prompt in test_prompts:
    emotion, conf = detect_emotion(prompt)
    print(f"\n[Test: {label}]")
    print(f"User Prompt: '{prompt}'")
    print(f"Detected Emotion: {emotion} (Confidence: {conf})")

    res = llm_assistant.process_chat(db, user_query=prompt, session_id=f"test_{emotion}")
    print(f"Assistant Response:\n{res['response']}")
    print("Suggested Books:")
    for b in res.get("suggested_books", []):
        print(f"  - {b['title']} by {b.get('authors')} ({b.get('categories')}) [Stock: {b.get('copies_available')}]")
    print("-" * 50)

db.close()
