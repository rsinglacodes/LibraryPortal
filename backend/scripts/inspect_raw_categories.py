import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from collections import Counter
from sqlalchemy import select
from app.database.connection import get_session_local
from app.models import Book

db = get_session_local()()
records = db.scalars(select(Book.categories).where(Book.categories.is_not(None))).all()
cat_counts = Counter()
for rec in records:
    for cat in rec.split(","):
        c = cat.strip()
        if c:
            cat_counts[c] += 1

print("Top 30 raw categories in DB:")
for c, cnt in cat_counts.most_common(30):
    print(f"  {c}: {cnt}")

db.close()
