"""Import library_combined_dataset.csv into Neon (users, books, ratings)."""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Book, Rating, User

SCRIPT_DIR = Path(__file__).resolve().parent
DATASET_PATH = SCRIPT_DIR.parent / "data" / "library_combined_dataset.csv"
BATCH_SIZE = 2000


def _optional_str(value) -> str | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    text_value = str(value).strip()
    if not text_value or text_value.lower() == "nan":
        return None
    return text_value


def _optional_int(value) -> int | None:
    text_value = _optional_str(value)
    if text_value is None:
        return None
    try:
        return int(float(text_value))
    except ValueError:
        return None


def _optional_float(value) -> float | None:
    text_value = _optional_str(value)
    if text_value is None:
        return None
    try:
        return float(text_value)
    except ValueError:
        return None


def load_dataset() -> pd.DataFrame:
    df = pd.read_csv(DATASET_PATH, dtype=str)
    required = {
        "user_id",
        "isbn10",
        "title",
        "rating",
        "name",
        "email",
        "password",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Dataset missing columns: {sorted(missing)}")

    df["isbn10"] = df["isbn10"].astype(str).str.strip()
    df["user_id"] = df["user_id"].astype(str).str.strip()
    if (df["isbn10"] == "").any() or df["isbn10"].isna().any():
        raise ValueError("Dataset contains empty isbn10 values")
    return df


def build_users(df: pd.DataFrame) -> list[dict]:
    users = (
        df[["user_id", "name", "email", "password"]]
        .drop_duplicates(subset=["user_id"], keep="first")
        .copy()
    )
    rows: list[dict] = []
    for row in users.itertuples(index=False):
        rows.append(
            {
                "roll_number": str(row.user_id),
                "name": str(row.name),
                "email": str(row.email),
                "password_hash": str(row.password),
            }
        )
    return rows


def build_books(df: pd.DataFrame) -> list[dict]:
    books = df.drop_duplicates(subset=["isbn10"], keep="first")
    rows: list[dict] = []
    for row in books.itertuples(index=False):
        rows.append(
            {
                "isbn10": str(row.isbn10),
                "title": str(row.title),
                "subtitle": _optional_str(getattr(row, "subtitle", None)),
                "authors": _optional_str(getattr(row, "authors", None)),
                "categories": _optional_str(getattr(row, "categories", None)),
                "description": _optional_str(getattr(row, "description", None)),
                "thumbnail": _optional_str(getattr(row, "thumbnail", None)),
                "published_year": _optional_int(getattr(row, "published_year", None)),
                "num_pages": _optional_int(getattr(row, "num_pages", None)),
                "average_rating": _optional_float(getattr(row, "average_rating", None)),
                "ratings_count": _optional_int(getattr(row, "ratings_count", None)),
            }
        )
    return rows


def build_ratings(df: pd.DataFrame) -> list[dict]:
    # Keep rating=0 rows: schema allows 0 and the recommendation model
    # treats 0 as "no explicit rating" at inference time.
    ratings = (
        df[["user_id", "isbn10", "rating"]]
        .drop_duplicates(subset=["user_id", "isbn10"], keep="first")
        .copy()
    )
    rows: list[dict] = []
    for row in ratings.itertuples(index=False):
        rating_value = _optional_int(row.rating)
        if rating_value is None:
            raise ValueError(f"Invalid rating for user={row.user_id} isbn10={row.isbn10}")
        rows.append(
            {
                "roll_number": str(row.user_id),
                "isbn10": str(row.isbn10),
                "rating": rating_value,
            }
        )
    return rows


def insert_batches(session: Session, table, rows: list[dict], label: str) -> None:
    total = len(rows)
    for start in range(0, total, BATCH_SIZE):
        batch = rows[start : start + BATCH_SIZE]
        session.execute(insert(table).values(batch))
        session.commit()
        print(f"  {label}: {min(start + BATCH_SIZE, total):,}/{total:,}")


def verify(session: Session) -> None:
    users = session.execute(text("SELECT COUNT(*) FROM users")).scalar_one()
    books = session.execute(text("SELECT COUNT(*) FROM books")).scalar_one()
    ratings = session.execute(text("SELECT COUNT(*) FROM ratings")).scalar_one()
    orphan_ratings = session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM ratings r
            LEFT JOIN books b ON b.isbn10 = r.isbn10
            LEFT JOIN users u ON u.roll_number = r.roll_number
            WHERE b.isbn10 IS NULL OR u.roll_number IS NULL
            """
        )
    ).scalar_one()
    zero_ratings = session.execute(
        text("SELECT COUNT(*) FROM ratings WHERE rating = 0")
    ).scalar_one()
    positive_ratings = session.execute(
        text("SELECT COUNT(*) FROM ratings WHERE rating BETWEEN 1 AND 10")
    ).scalar_one()

    print("\nVerification")
    print(f"  users: {users:,}")
    print(f"  books: {books:,}")
    print(f"  ratings: {ratings:,}")
    print(f"  orphan ratings: {orphan_ratings:,}")
    print(f"  rating = 0: {zero_ratings:,}")
    print(f"  rating 1-10: {positive_ratings:,}")

    if users != 14536 or books != 2442:
        raise RuntimeError(
            f"Unexpected counts: users={users}, books={books} "
            "(expected users=14536, books=2442)"
        )
    if orphan_ratings != 0:
        raise RuntimeError(f"Found {orphan_ratings} orphan ratings")


def main() -> None:
    print(f"Loading dataset: {DATASET_PATH}")
    df = load_dataset()
    print(f"Rows: {len(df):,}")

    users = build_users(df)
    books = build_books(df)
    ratings = build_ratings(df)
    print(f"Prepared users={len(users):,}, books={len(books):,}, ratings={len(ratings):,}")

    engine = create_engine(get_settings().DATABASE_URL)
    with Session(engine) as session:
        existing = {
            "users": session.execute(text("SELECT COUNT(*) FROM users")).scalar_one(),
            "books": session.execute(text("SELECT COUNT(*) FROM books")).scalar_one(),
            "ratings": session.execute(text("SELECT COUNT(*) FROM ratings")).scalar_one(),
        }
        if any(existing.values()):
            raise RuntimeError(
                "Database is not empty. Refusing to import. "
                f"Current counts: {existing}"
            )

        print("Importing users...")
        insert_batches(session, User.__table__, users, "users")
        print("Importing books...")
        insert_batches(session, Book.__table__, books, "books")
        print("Importing ratings...")
        insert_batches(session, Rating.__table__, ratings, "ratings")
        verify(session)

    print("\nImport complete.")


if __name__ == "__main__":
    main()
