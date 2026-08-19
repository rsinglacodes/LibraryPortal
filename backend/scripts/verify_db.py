from __future__ import annotations

import sys
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent))

from app.core.config import get_settings

def verify():
    engine = create_engine(get_settings().DATABASE_URL)
    with Session(engine) as session:
        users = session.execute(text("SELECT COUNT(*) FROM users")).scalar_one()
        books = session.execute(text("SELECT COUNT(*) FROM books")).scalar_one()
        ratings = session.execute(text("SELECT COUNT(*) FROM ratings")).scalar_one()
        orphans = session.execute(
            text(
                "SELECT COUNT(*) FROM ratings r "
                "LEFT JOIN books b ON b.isbn10 = r.isbn10 "
                "LEFT JOIN users u ON u.roll_number = r.roll_number "
                "WHERE b.isbn10 IS NULL OR u.roll_number IS NULL"
            )
        ).scalar_one()
        zeros = session.execute(text("SELECT COUNT(*) FROM ratings WHERE rating = 0")).scalar_one()
        positives = session.execute(text("SELECT COUNT(*) FROM ratings WHERE rating BETWEEN 1 AND 10")).scalar_one()

        print(f"Neon Database Summary:")
        print(f"  Users: {users:,}")
        print(f"  Books: {books:,}")
        print(f"  Ratings: {ratings:,}")
        print(f"  Orphans: {orphans}")
        print(f"  Rating=0: {zeros:,}")
        print(f"  Rating=1..10: {positives:,}")

if __name__ == "__main__":
    verify()
